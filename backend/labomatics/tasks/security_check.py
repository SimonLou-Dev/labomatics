"""Tâche Celery quotidienne — issue #61.

Contrôle la cohérence des IP WAN (Proxmox vs DB) et, en même temps, migre
progressivement les labs déployés avant le durcissement de l'issue #78 vers
la configuration sécurisée (pool système, firewall VM, IPSet, ACL minimale) —
décision actée dans les commentaires des issues #61/#78. Réaligne aussi
chaque jour le groupe/rôle Proxmox et les ACL propres de chaque student
(`ProxmoxAclClient.ensure_student_defaults`/`set_student`), pour corriger
toute dérive manuelle sur le cluster. Purge aussi les audit logs de plus
d'un mois.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from labomatics.constants.enums import EventType
from labomatics.core.config.settings import settings
from labomatics.core.db.models.lab_provisioning import LabProvisioning
from labomatics.core.db.repository.audit_log import AuditLogRepository
from labomatics.core.db.repository.lab_provisioning import LabProvisioningRepository
from labomatics.helpers.proxmox._root import LabomaticsProxmoxClient, sanitize_pool_name
from labomatics.helpers.proxmox.acl import STUDENT_GROUP
from labomatics.helpers.proxmox.firewall import normalize_host_cidr
from labomatics.helpers.proxmox.router_security import apply_router_security
from labomatics.services.audit_service import AuditService
from labomatics.worker.broker import celery_app
from labomatics.worker.jobs import run_async

logger = logging.getLogger(__name__)

AUDIT_LOG_RETENTION_DAYS = 30


async def _check_and_remediate_lab(
    proxmox: LabomaticsProxmoxClient, lab: LabProvisioning, audit_svc: AuditService
) -> None:
    """Contrôle/remédie un seul lab : IP WAN, pool, firewall, ACL."""
    lab_prov_repo = LabProvisioningRepository()

    if not lab.proxmox_vm_id or not lab.ip_allocation:
        return

    vmid = lab.proxmox_vm_id
    wan_ip = str(lab.ip_allocation.ip_address)

    try:
        node = await proxmox.vm.find_node(vmid)
        if not node:
            await lab_prov_repo.update(
                lab.id,
                {
                    "last_checked_at": datetime.now(UTC).replace(tzinfo=None),
                    "last_error": "VM Proxmox introuvable",
                },
            )
            return

        # 1. Comparaison IP WAN Proxmox vs DB (contrôle d'origine de #61).
        wanted = {f"{wan_ip}/32"}
        current_entries = await proxmox.firewall.get_ipset_entries(
            node, vmid, "ipfilter-net0"
        )
        if {normalize_host_cidr(c) for c in current_entries} != {
            normalize_host_cidr(c) for c in wanted
        }:
            logger.warning(
                f"WAN IP mismatch for lab {lab.id}: "
                f"expected {wanted}, found {current_entries}"
            )
            await audit_svc.log(
                actor_keycloak_id=lab.owner_keycloak_id,
                actor_role=lab.owner_role,
                action=EventType.WAN_IP_MISMATCH,
                resource_type="lab_provisioning",
                resource_id=lab.id,
                details={"expected": list(wanted), "found": list(current_entries)},
            )

        # 2. Remédiation #78 : routeur encore dans le pool étudiant ?
        current_pool: str | None = None
        if lab.student:
            student_pool = sanitize_pool_name(lab.student.login)
            user_id = f"{student_pool}@{settings.keycloak_realm}"
            members = await proxmox.pool.get_vms(student_pool)
            if any(int(m.get("vmid", -1)) == vmid for m in members):
                current_pool = student_pool

            # 3. Réalignement des permissions student (groupe + ACL propres),
            # re-appliquées sans condition pour corriger toute dérive manuelle.
            if lab.proxmox_vnet and lab.cluster:
                try:
                    await proxmox.acl.set_student(
                        zone=lab.cluster.sdn_zone,
                        vnet=lab.proxmox_vnet,
                        user_pool=student_pool,
                        user_id=user_id,
                    )
                    await proxmox.user.ensure_in_group(user_id, STUDENT_GROUP)
                except RuntimeError as e:
                    logger.warning(
                        f"Failed to realign Proxmox permissions for lab {lab.id}: {e}"
                    )

            await apply_router_security(
                proxmox,
                node=node,
                vmid=vmid,
                user_id=user_id,
                wan_ip=wan_ip,
                current_pool=current_pool,
            )
            if current_pool:
                logger.info(f"Migrated router of lab {lab.id} out of {current_pool}")
                await audit_svc.log(
                    actor_keycloak_id=lab.owner_keycloak_id,
                    actor_role=lab.owner_role,
                    action=EventType.ROUTER_SECURITY_REMEDIATED,
                    resource_type="lab_provisioning",
                    resource_id=lab.id,
                    details={"migrated_from_pool": current_pool},
                )

        await lab_prov_repo.update(
            lab.id,
            {
                "last_checked_at": datetime.now(UTC).replace(tzinfo=None),
                "last_error": None,
            },
        )
    except Exception as e:
        logger.error(f"Security check failed for lab {lab.id}: {e}")
        await lab_prov_repo.update(
            lab.id,
            {
                "last_checked_at": datetime.now(UTC).replace(tzinfo=None),
                "last_error": str(e),
            },
        )


async def _daily_security_check() -> None:
    """Itère tous les labs actifs (regroupés par cluster) puis purge l'audit log."""
    audit_svc = AuditService()
    lab_prov_repo = LabProvisioningRepository()
    labs = await lab_prov_repo.list_active_with_cluster_and_ip()

    labs_by_cluster: dict[UUID, list[LabProvisioning]] = {}
    for lab in labs:
        labs_by_cluster.setdefault(lab.cluster_id, []).append(lab)

    for cluster_id, cluster_labs in labs_by_cluster.items():
        cluster = cluster_labs[0].cluster
        if not cluster or not cluster.credential:
            logger.warning(f"Cluster {cluster_id} has no credential, skipping")
            continue

        try:
            proxmox = LabomaticsProxmoxClient(cluster)
        except ValueError as e:
            logger.error(f"Failed to connect to cluster {cluster_id}: {e}")
            continue

        try:
            await proxmox.ensure_student_baseline()
        except RuntimeError as e:
            logger.error(
                f"Failed to ensure student role/group on cluster {cluster_id}: {e}"
            )

        try:
            for lab in cluster_labs:
                await _check_and_remediate_lab(proxmox, lab, audit_svc)
        finally:
            await proxmox.close()

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(
        days=AUDIT_LOG_RETENTION_DAYS
    )
    deleted = await AuditLogRepository().delete_older_than(cutoff)
    logger.info(f"Purged {deleted} audit log entries older than {cutoff.isoformat()}")


@celery_app.task(name="labomatics.daily_security_check")
def daily_security_check() -> dict:
    """Tâche Celery quotidienne : contrôle/remédiation réseau + purge audit log."""
    run_async(_daily_security_check())
    return {"status": "done"}
