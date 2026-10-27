"""Service pour la gestion des labs.

Orchestration de la création de labs pour students/teachers/admins.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status

from labomatics.api.dto.auth import AuthUser
from labomatics.api.dto.lab import LabDataDTO, LabOwnerDTO, LabVmDTO
from labomatics.api.dto.notification import JobDTO
from labomatics.constants.enums import EventType, OwnerRole
from labomatics.core.db.models.lab_provisioning import LabProvisioning
from labomatics.core.db.repository.cohort_cluster import CohortClusterRepository
from labomatics.core.db.repository.student import StudentRepository
from labomatics.core.db.repository.teacher_cohort import TeacherCohortRepository
from labomatics.services.audit_service import AuditService
from labomatics.tasks import lab as lab_tasks
from labomatics.worker.jobs import new_job_id

logger = logging.getLogger(__name__)


class LabService:
    """Service pour la gestion des labs."""

    def __init__(self, audit_service: AuditService | None = None) -> None:
        """Initialise le service.

        Args:
            audit_service: AuditService (créé si None).
        """
        self.audit_service = audit_service or AuditService()

    async def _resolve_owner(self, user: AuthUser) -> tuple[OwnerRole, object | None]:
        """Détermine le rôle et les infos du propriétaire du lab.

        Retourne (owner_role, student_obj). student_obj est None si teacher/admin.

        Args:
            user: Utilisateur authentifié (AuthUser).

        Returns:
            Tuple (OwnerRole, student_obj ou None).
        """
        student_repo = StudentRepository()

        # Chercher un Student via keycloak_user_id
        student = await student_repo.get_by_keycloak_id(UUID(user.subject))

        if student:
            logger.info(f"User {user.username} resolved as STUDENT")
            return OwnerRole.STUDENT, student

        # Chercher un Teacher (TeacherCohort)
        teacher_repo = TeacherCohortRepository()
        teacher_cohorts = await teacher_repo.list_by_teacher_keycloak_id(
            UUID(user.subject)
        )
        if teacher_cohorts:
            logger.info(f"User {user.username} resolved as TEACHER")
            return OwnerRole.TEACHER, None

        # Sinon Admin (pas de vérification supplémentaire, Keycloak le gère)
        logger.info(f"User {user.username} resolved as ADMIN")
        return OwnerRole.ADMIN, None

    async def _ensure_cluster_allowed_for_student(
        self, student: object, cluster_id: UUID
    ) -> None:
        """Vérifie que le cluster demandé fait partie de la promo de l'étudiant.

        Args:
            student: Étudiant résolu (objet Student).
            cluster_id: Cluster explicitement demandé par l'appelant.

        Raises:
            HTTPException 403: Si l'étudiant n'a pas d'enrollment actif, ou si le
                cluster n'est pas assigné à la promo de cet enrollment.
        """
        student_repo = StudentRepository()
        student_with_enrollments = await student_repo.get_by_id_with_enrollments(
            student.id
        )
        active_enroll = next(
            (
                e
                for e in (
                    student_with_enrollments.enrollments
                    if student_with_enrollments
                    else []
                )
                if e.is_active()
            ),
            None,
        )
        if not active_enroll:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Aucun enrollment actif pour cet étudiant",
            )

        cohort_cluster_repo = CohortClusterRepository()
        cohort_clusters = await cohort_cluster_repo.list_by_cohort(
            active_enroll.cohort.id
        )
        allowed_cluster_ids = {cc.cluster_id for cc in cohort_clusters}
        if cluster_id not in allowed_cluster_ids:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Ce cluster n'est pas assigné à la promotion de l'étudiant",
            )

    async def create(
        self,
        user: AuthUser,
        cluster_id: UUID | str | None = None,
        access_origin: str = "self_service",
    ) -> JobDTO:
        """Crée un lab pour un utilisateur (student/teacher/admin).

        Args:
            user: Utilisateur authentifié (AuthUser du token Keycloak).
            cluster_id: ID du cluster Proxmox (optionnel, auto-résolu pour students).
            access_origin: Origine de la demande ("self_service" par défaut).

        Returns:
            JobDTO avec le jobId pour suivre l'exécution.

        Raises:
            HTTPException 403: Si un étudiant demande un cluster hors de sa promo.
        """
        owner_role, student = await self._resolve_owner(user)

        if owner_role == OwnerRole.STUDENT and cluster_id:
            await self._ensure_cluster_allowed_for_student(
                student, UUID(str(cluster_id))
            )
        elif owner_role != OwnerRole.STUDENT and not cluster_id:
            # tasks/lab.py::_create_lab lève sinon une ValueError *dans* le job
            # Celery : l'utilisateur ne voit qu'un échec asynchrone opaque.
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"cluster_id requis pour un {owner_role}",
            )

        # Convertir cluster_id en string si UUID
        cluster_id_str = str(cluster_id) if cluster_id else None

        # Log de la requête AVANT enqueue (audit trail)
        await self.audit_service.log(
            actor_keycloak_id=user.subject,
            actor_role=str(owner_role),
            action=EventType.LAB_REQUESTED,
            resource_type="lab",
            resource_id=None,
            details={
                "cluster_id": cluster_id_str,
                "owner_role": str(owner_role),
                "access_origin": access_origin,
            },
        )

        # Enqueue le job Celery
        job_id = new_job_id()
        logger.info(f"Enqueueing lab creation job {job_id} for user {user.username}")

        # Tracker la tâche dans Redis
        from labomatics.services.job_service import JobService

        JobService._start_task(
            job_id,
            user.subject,
            "lab_deploy",
            f"Création lab ({str(owner_role).lower()})",
        )

        lab_tasks.create_lab.delay(
            owner_keycloak_id=user.subject,
            owner_role=str(owner_role),
            owner_username=user.username,
            owner_email=user.email,
            student_id=str(student.id) if student else None,
            cluster_id=cluster_id_str,
            access_origin=access_origin,
            job_id=job_id,
            task_id=job_id,
        )

        return JobDTO(jobId=job_id)

    @staticmethod
    def build_owner_lab_data(
        user: AuthUser, provisioning: LabProvisioning
    ) -> LabDataDTO:
        """Construit le LabDataDTO pour un owner non-student (teacher/admin).

        Miroir de `StudentService.get_lab_data`, sans cohort/enrollment : le
        `provisioning` doit être chargé avec `cluster`, `ip_allocation`,
        `vxlan_allocation` et `vms` (voir
        `LabProvisioningRepository.get_by_owner_keycloak_id`).
        """
        vms = [
            LabVmDTO(
                id=str(vm.id),
                name=vm.name,
                cluster_name=vm.cluster_name,
                state=vm.state,
                cores=vm.cores,
                memory=vm.memory,
                disk=vm.disk,
                created_at=vm.created_at,
                notes=vm.notes,
            )
            for vm in provisioning.vms
        ]

        wan_ip = (
            str(provisioning.ip_allocation.ip_address)
            if provisioning.ip_allocation
            else None
        )
        vxlan_tag = (
            provisioning.vxlan_allocation.vni if provisioning.vxlan_allocation else None
        )
        openwrt_link = f"https://{wan_ip}:1337/cgi-bin/luci/" if wan_ip else None
        proxmox_url = provisioning.cluster.url if provisioning.cluster else None

        # AuthUser (claims JWT) ne porte pas prénom/nom séparément, contrairement
        # à Student (profil Keycloak complet non re-fetché ici pour rester léger).
        owner_dto = LabOwnerDTO(
            id=user.subject,
            login=user.username,
            first_name=user.username,
            last_name="",
            email=user.email,
            role=OwnerRole(provisioning.owner_role),
            cohort_name=None,
            created_at=provisioning.created_at,
        )

        return LabDataDTO(
            owner=owner_dto,
            vms=vms,
            wan_ip=wan_ip,
            vxlan_tag=vxlan_tag,
            openwrt_link=openwrt_link,
            proxmox_url=proxmox_url,
        )
