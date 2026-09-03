"""Tasks Celery pour la création de labs."""

from __future__ import annotations

import logging
from datetime import datetime
from ipaddress import IPv4Network
from uuid import UUID

from labomatics.constants.enums import EventType, OwnerRole
from labomatics.core.config.settings import settings
from labomatics.core.db.models.ip_allocation import IpAllocation
from labomatics.core.db.models.lab_provisioning import LabProvisioning
from labomatics.core.db.models.lab_vm import LabVm
from labomatics.core.db.models.vxlan_allocation import VxlanAllocation
from labomatics.core.db.repository.cluster import ClusterRepository
from labomatics.core.db.repository.cohort_cluster import CohortClusterRepository
from labomatics.core.db.repository.ip_allocation import IpAllocationRepository
from labomatics.core.db.repository.lab_provisioning import LabProvisioningRepository
from labomatics.core.db.repository.lab_vm import LabVmRepository
from labomatics.core.db.repository.student import StudentRepository
from labomatics.core.db.repository.vxlan_allocation import VxlanAllocationRepository
from labomatics.helpers.proxmox._root import LabomaticsProxmoxClient
from labomatics.helpers.proxmox.api.types import CloudInitConfigDTO
from labomatics.services.audit_service import AuditService
from labomatics.services.ip_range_service import IpRangeService
from labomatics.services.network_range_service import NetworkRangeService
from labomatics.services.vxlan_range_service import VxlanRangeService
from labomatics.worker.broker import celery_app
from labomatics.worker.jobs import emit, run_async

logger = logging.getLogger(__name__)

OPENWRT_TEMPLATE_ID = 90200


async def _create_lab(
    owner_keycloak_id: str,
    owner_role: str,
    owner_username: str,
    owner_email: str,
    student_id: str | None,
    cluster_id: str | None,
    access_origin: str,
    job_id: str | None = None,
) -> None:
    """Crée un lab complet pour un utilisateur.

    Orchestre : allocation IP/VNI, création Proxmox (user + pool + vnet SDN + VM clone),
    config cloud-init, démarrage VM, finalisation DB, audit trail.

    En cas d'erreur à tout moment : met à jour LabProvisioning.status="error",
    log un LAB_CREATION_FAILED event, et re-lève pour Celery.

    """
    audit_svc = AuditService()
    lab_prov_repo = LabProvisioningRepository()
    lab_vm_repo = LabVmRepository()

    lab_provisioning = None
    proxmox = None

    try:
        # 1. Résolution du cluster
        cluster_repo = ClusterRepository()
        if cluster_id:
            cluster = await cluster_repo.get_with_ranges(UUID(cluster_id))
            if not cluster:
                raise ValueError(f"Cluster {cluster_id} not found")
        else:
            # Auto-résolution pour student uniquement
            if owner_role != str(OwnerRole.STUDENT):
                raise ValueError(f"cluster_id is required for {owner_role}")

            student_repo = StudentRepository()
            student = await student_repo.get_by_id_with_enrollments(UUID(student_id))
            if not student or not student.enrollments:
                raise ValueError(f"Student {student_id} has no active enrollment")

            # Trouver l'enrollment actif
            now = datetime.now()
            active_enroll = next(
                (e for e in student.enrollments if e.start_date <= now <= e.end_date),
                None,
            )
            if not active_enroll:
                raise ValueError(f"Student {student_id} has no active enrollment")

            # Trouver le cluster par défaut de la promo
            cohort_cluster_repo = CohortClusterRepository()
            cohort_clusters = await cohort_cluster_repo.list_by_cohort(
                active_enroll.cohort.id
            )
            default_cc = next((cc for cc in cohort_clusters if cc.is_default), None)
            if not default_cc:
                raise ValueError(
                    f"No default cluster for cohort {active_enroll.cohort.name}"
                )

            cluster = await cluster_repo.get_with_ranges(default_cc.cluster_id)

        # 2. Vérifier si un lab existe déjà pour ce student+cluster
        if student_id:
            existing_lab = await lab_prov_repo.get_by_student_cluster(
                UUID(student_id), cluster.id
            )
            if existing_lab:
                if existing_lab.status == "active":
                    await emit(job_id, "done", message="Lab already exists")
                    logger.info(
                        f"Lab already exists for student {student_id} on cluster {cluster.id}"
                    )
                    return
                elif existing_lab.status == "provisioning":
                    await emit(job_id, "done", message="Lab creation in progress")
                    logger.info(
                        f"Lab provisioning already in progress for student {student_id}"
                    )
                    return
                elif existing_lab.status == "error":
                    # Supprimer l'ancien lab en erreur et créer un nouveau
                    if existing_lab.ip_allocation_id:
                        await IpAllocationRepository().delete(
                            existing_lab.ip_allocation_id
                        )
                    if existing_lab.vxlan_allocation_id:
                        await VxlanAllocationRepository().delete(
                            existing_lab.vxlan_allocation_id
                        )
                    await lab_prov_repo.delete(existing_lab.id)
                    logger.info(
                        f"Deleted failed lab {existing_lab.id}, creating new one"
                    )

        # 3. Résolution des ranges IP et VXLAN du cluster
        if not cluster.ip_range_clusters or not cluster.vxlan_range_clusters:
            raise ValueError(f"Cluster {cluster.name} has no IP or VXLAN ranges")

        ip_range_cluster = cluster.ip_range_clusters[0]
        vxlan_range_cluster = cluster.vxlan_range_clusters[0]

        # 4. Créer LabProvisioning (status=provisioning)
        lab_provisioning = LabProvisioning(
            owner_keycloak_id=UUID(owner_keycloak_id),
            owner_role=owner_role,
            student_id=UUID(student_id) if student_id else None,
            cluster_id=cluster.id,
            status="provisioning",
            access_origin=access_origin,
        )
        lab_provisioning = await lab_prov_repo.add(lab_provisioning)
        await emit(job_id, "step_done", step="lab_provisioning_created")

        # 5. Allocation IP WAN
        ip_svc = IpRangeService()
        wan_ip = await ip_svc.get_first_available_ip(
            ip_range_cluster.ip_range_id, cluster.id
        )

        ip_alloc = IpAllocation(
            ip_range_cluster_id=ip_range_cluster.id,
            owner_keycloak_id=UUID(owner_keycloak_id),
            owner_role=owner_role,
            student_id=UUID(student_id) if student_id else None,
            ip_address=str(wan_ip),
        )
        ip_alloc = await IpAllocationRepository().add(ip_alloc)
        await lab_prov_repo.update(
            lab_provisioning.id, {"ip_allocation_id": ip_alloc.id}
        )

        await audit_svc.log(
            actor_keycloak_id=owner_keycloak_id,
            actor_role=owner_role,
            action=EventType.WAN_IP_ALLOCATED,
            resource_type="lab_provisioning",
            resource_id=str(lab_provisioning.id),
            details={"ip_address": str(wan_ip)},
        )
        await emit(job_id, "step_done", step="wan_ip_allocated", message=str(wan_ip))

        # 6. Allocation VNI + subnet
        vxlan_svc = VxlanRangeService()
        vni = await vxlan_svc.get_first_available_vni(
            vxlan_range_cluster.vxlan_range_id, cluster.id
        )

        base_net = IPv4Network(
            vxlan_range_cluster.vxlan_range.base_network, strict=False
        )
        subnet = NetworkRangeService._calculate_subnet(base_net, vni)

        vxlan_alloc = VxlanAllocation(
            vxlan_range_cluster_id=vxlan_range_cluster.id,
            owner_keycloak_id=UUID(owner_keycloak_id),
            owner_role=owner_role,
            student_id=UUID(student_id) if student_id else None,
            vni=vni,
            subnet=str(subnet),
        )
        vxlan_alloc = await VxlanAllocationRepository().add(vxlan_alloc)
        await lab_prov_repo.update(
            lab_provisioning.id, {"vxlan_allocation_id": vxlan_alloc.id}
        )

        await audit_svc.log(
            actor_keycloak_id=owner_keycloak_id,
            actor_role=owner_role,
            action=EventType.NETWORK_ALLOCATED,
            resource_type="lab_provisioning",
            resource_id=str(lab_provisioning.id),
            details={"vni": vni, "subnet": str(subnet)},
        )
        await emit(job_id, "step_done", step="network_allocated", message=str(subnet))

        # 7. Connexion Proxmox (créé dans la boucle asyncio courante)
        try:
            proxmox = LabomaticsProxmoxClient(cluster)
        except ValueError as e:
            raise RuntimeError(f"Failed to initialize Proxmox client: {e}") from e

        # 8. Créer user + pool + vnet SDN + ACL + token
        # Sanitize username pour Proxmox
        user_name = (
            student.login
            if student_id
            else "".join(
                c.lower() if c.isalnum() or c in "-_" else "_" for c in owner_username
            )[:16]
        )

        # Calculer la gateway (dernière IP utilisable du subnet)
        gateway_ip = subnet[-2]  # subnet[-1] est le broadcast

        await proxmox.create_user_with_deps(
            user_name=user_name,
            realm=settings.keycloak_realm,
            zone=cluster.sdn_zone,
            tag=vni,
            gateway=str(gateway_ip),
            subnet=str(subnet),
        )
        await emit(job_id, "step_done", step="proxmox_user_created")

        # 9. Clone la VM OpenWRT (ou récupérer si elle existe déjà)
        vm_name = f"router-{user_name}"
        # Chercher si la VM existe déjà
        existing_node = await proxmox.vm.find_node_by_name(vm_name)
        if existing_node:
            dest_node = existing_node
            vmid = await proxmox.vm.find_vmid_by_name(vm_name)
            if vmid is None:
                raise RuntimeError(f"VM {vm_name} found but VMID not resolved")
            logger.info(f"VM {vm_name} already exists (vmid={vmid}), skipping clone")
        else:
            dest_node, vmid = await proxmox.vm.clone(
                vm_name=vm_name,
                vm_storage=cluster.default_storage,
                source_id=OPENWRT_TEMPLATE_ID,
                pool=user_name,
                full_clone=True,
            )
        await emit(job_id, "step_done", step="vm_cloned", message=f"vmid={vmid}")

        # 10. Configurer cloud-init
        wan_ip_obj = ip_range_cluster.ip_range
        # wan_ip_obj.network est un IPv4Network object, donc prefixlen donne le /24
        wan_network = IPv4Network(wan_ip_obj.network, strict=False)
        wan_prefix = wan_network.prefixlen
        wan_gateway = str(wan_ip_obj.gateway)

        vnet_name = f"vn{vni}"

        cloud_init_cfg = CloudInitConfigDTO(
            cores=2,
            memory=512,
            storage_device=cluster.default_storage,
            wan_ip=str(wan_ip),
            wan_prefix=int(wan_prefix),
            wan_gateway=wan_gateway,
            vxlan_gateway_ip=str(gateway_ip),
            wan_bridge=cluster.wan_bridge,
            vnet_bridge=vnet_name,
            tags="labomatics-system",
            onboot=True,
        )

        await proxmox.vm.config(dest_node, vmid, **cloud_init_cfg.to_proxmox_args())
        await emit(job_id, "step_done", step="vm_configured")

        await audit_svc.log(
            actor_keycloak_id=owner_keycloak_id,
            actor_role=owner_role,
            action=EventType.ROUTER_CREATED,
            resource_type="lab_provisioning",
            resource_id=str(lab_provisioning.id),
            details={"vmid": vmid, "node": dest_node},
        )

        # 11. Démarrer la VM
        await proxmox.vm.start(dest_node, vmid)
        await emit(job_id, "step_done", step="vm_started")

        # 12. Récupérer la config finale et créer LabVm
        config = await proxmox.vm.get_config(dest_node, vmid)
        disk_size_gb = proxmox.vm.get_disk_size_gb(config)

        lab_vm = LabVm(
            lab_provisioning_id=lab_provisioning.id,
            name=f"router-{user_name}",
            cluster_name=cluster.name,
            state="running",
            cores=2,
            memory=512,
            disk=disk_size_gb,
        )
        lab_vm = await lab_vm_repo.add(lab_vm)

        # 13. Finaliser LabProvisioning
        await lab_prov_repo.update(
            lab_provisioning.id,
            {
                "status": "active",
                "proxmox_pool": user_name,
                "proxmox_vm_id": vmid,
                "proxmox_vnet": vnet_name,
                "last_checked_at": datetime.now(),
            },
        )

        # 14. Audit trail final
        await audit_svc.log(
            actor_keycloak_id=owner_keycloak_id,
            actor_role=owner_role,
            action=EventType.LAB_CREATED,
            resource_type="lab_provisioning",
            resource_id=str(lab_provisioning.id),
            details={"vmid": vmid, "node": dest_node, "vnet": vnet_name},
        )
        await emit(job_id, "done", message="Lab created successfully")

        logger.info(f"Lab created for {owner_username}: vmid={vmid}, vnet={vnet_name}")

    except Exception as e:
        logger.error(f"Lab creation failed for {owner_username}: {e}", exc_info=True)

        # Mettre à jour status en DB si lab_provisioning existe
        if lab_provisioning:
            try:
                await lab_prov_repo.update(
                    lab_provisioning.id,
                    {"status": "error", "last_error": str(e)},
                )
            except Exception as db_err:
                logger.error(f"Failed to update lab_provisioning status: {db_err}")

        # Log audit failure
        try:
            await AuditService().log(
                actor_keycloak_id=owner_keycloak_id,
                actor_role=owner_role,
                action=EventType.LAB_CREATION_FAILED,
                resource_type="lab_provisioning",
                resource_id=str(lab_provisioning.id) if lab_provisioning else None,
                details={"error": str(e)},
            )
        except Exception as audit_err:
            logger.warning(f"Failed to log audit failure: {audit_err}")

        await emit(job_id, "error", message=str(e))
        raise

    finally:
        if proxmox:
            await proxmox.close()


@celery_app.task(name="labomatics.create_lab")
def create_lab(
    owner_keycloak_id: str,
    owner_role: str,
    owner_username: str,
    owner_email: str,
    student_id: str | None,
    cluster_id: str | None,
    access_origin: str,
    job_id: str | None = None,
) -> None:
    """Tâche Celery pour créer un lab."""
    run_async(
        _create_lab(
            owner_keycloak_id=owner_keycloak_id,
            owner_role=owner_role,
            owner_username=owner_username,
            owner_email=owner_email,
            student_id=student_id,
            cluster_id=cluster_id,
            access_origin=access_origin,
            job_id=job_id,
        )
    )
