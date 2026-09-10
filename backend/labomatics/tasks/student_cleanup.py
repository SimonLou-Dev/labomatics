"""Tasks Celery pour la suppression d'étudiants et leurs ressources."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from labomatics.constants.enums import EventType
from labomatics.core.config.settings import settings
from labomatics.core.db.models.lab_provisioning import LabProvisioning
from labomatics.core.db.models.student import Student
from labomatics.core.db.repository.ip_allocation import IpAllocationRepository
from labomatics.core.db.repository.lab_provisioning import LabProvisioningRepository
from labomatics.core.db.repository.student import StudentRepository
from labomatics.core.db.repository.vxlan_allocation import VxlanAllocationRepository
from labomatics.helpers.proxmox._root import LabomaticsProxmoxClient
from labomatics.services.keycloak_service import KeycloakService
from labomatics.worker.broker import celery_app
from labomatics.worker.jobs import emit, run_async

logger = logging.getLogger(__name__)


async def _delete_lab(
    lab: LabProvisioning,
    student: Student,
    job_id: str | None = None,
) -> None:
    ip_alloc_repo = IpAllocationRepository()
    vxlan_alloc_repo = VxlanAllocationRepository()
    lab_prov_repo = LabProvisioningRepository()

    # Use the cluster already loaded with credential via eager-loading
    cluster = lab.cluster
    if not cluster:
        raise ValueError(f"Cluster {lab.cluster_id} not found")
    proxmox = LabomaticsProxmoxClient(cluster)

    # 3. Récupérer et supprimer les VMs du pool
    logger.info(f"Fetching VMs from pool {student.login}")
    qemu_vms = await proxmox.pool.get_vms(student.login)
    lxc_vms = await proxmox.pool.get_lxcs(student.login)

    # Delete VMs (delete() now calls stop() first)
    for vm in qemu_vms:
        vmid = vm.get("vmid")
        node = vm.get("node")
        logger.info(f"Deleting QEMU VM {vmid} on node {node}")
        try:
            await proxmox.vm.delete(node=node, vmid=int(vmid))
        except Exception as e:
            logger.error(f"Failed to delete QEMU VM {vmid}: {e}")
            raise

    for ct in lxc_vms:
        vmid = ct.get("vmid")
        node = ct.get("node")
        logger.info(f"Deleting LXC container {vmid} on node {node}")
        try:
            await proxmox.vm.delete(node=node, vmid=int(vmid))
        except Exception as e:
            logger.error(f"Failed to delete LXC container {vmid}: {e}")
            raise

    # 4. Supprimer le user Proxmox
    user_id = f"{student.login}@{settings.keycloak_realm}"
    logger.info(f"Deleting Proxmox user {user_id}")
    try:
        await proxmox.user.delete(user_id)
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}")
        raise

    # 5. Supprimer le pool Proxmox
    logger.info(f"Deleting pool {student.login}")
    try:
        await proxmox.pool.delete(student.login)
    except Exception as e:
        logger.error(f"Failed to delete pool {student.login}: {e}")
        raise

    # 6. Cleanup de la DB
    logger.info(f"Cleaning up database records for student {student.login}")
    if lab.ip_allocation:
        await ip_alloc_repo.update(
            lab.ip_allocation.id, {"released_at": datetime.utcnow()}
        )
    if lab.vxlan_allocation:
        await vxlan_alloc_repo.update(
            lab.vxlan_allocation.id, {"released_at": datetime.utcnow()}
        )

    await lab_prov_repo.delete(lab.id)


async def _delete_student(student_id: str, job_id: str | None = None) -> None:
    """Supprime un étudiant et toutes ses ressources Proxmox.

    Orchestre : suppression des VMs, du user Proxmox, du pool,
    et cleanup de la DB (allocations IP/VXLAN, LabVm, LabProvisioning).

    En cas d'erreur : log l'événement et re-lève pour Celery.
    """

    student_repo = StudentRepository()

    keycloak_service = KeycloakService()

    student_uuid = UUID(student_id)

    try:
        # 1. Charger l'étudiant avec ses relations (eager loading)
        student = await student_repo.get_by_id_for_lab(student_uuid)
        if not student:
            raise ValueError(f"Student {student_id} not found")

        # le delete de keycloak

        if not student.lab_provisioning:
            logger.info(
                f"Student {student.login} has no lab provisioning, skipping Proxmox cleanup"
            )
            await student_repo.delete(student_uuid)
            return

        labs = student.lab_provisioning

        for lab in labs:
            try:
                await _delete_lab(lab, student, job_id)
            except Exception as e:
                logger.error(f"Impossible de delete  le lab {e}")

        # 7. Supprimer les enrollments (foreign key)
        from labomatics.core.db.repository.enrollment import EnrollmentRepository

        enrollment_repo = EnrollmentRepository()
        enrollments = await enrollment_repo.list_by_student(student_uuid)
        for enrollment in enrollments:
            await enrollment_repo.delete(enrollment.id)
        logger.info(f"Deleted {len(enrollments)} enrollments for {student.login}")

        # 8. Supprimer l'étudiant
        logger.info(f"Deleting student {student.login}")
        await student_repo.delete(student_uuid)

        try:
            await keycloak_service.delete_user(login=student.login)
        except Exception as e:
            logger.exception(
                f"Immpossible de supprimer le user {student.login} de keycloak : {e}"
            )

        # Audit
        await emit(
            job_id=job_id,
            event_type=EventType.STUDENT_DELETED,
            user_id=None,
            resource_type="student",
            resource_id=student_id,
            details={"login": student.login},
            severity="info",
        )

        logger.info(f"Successfully deleted student {student.login} and all resources")

    except Exception as e:
        logger.error(f"Student deletion failed for {student_id}: {e}")
        await emit(
            job_id=job_id,
            event_type=EventType.STUDENT_DELETION_FAILED,
            user_id=None,
            resource_type="student",
            resource_id=student_id,
            details={"error": str(e)},
            severity="error",
        )
        raise


@celery_app.task(name="labomatics.delete_student")
def delete_student(
    student_id: str, job_id: str | None = None, user_id: str | None = None
) -> dict:
    """Tâche Celery pour supprimer un étudiant."""
    return run_async(_delete_student(student_id=student_id, job_id=job_id))
