"""Service pour la gestion des labs.

Orchestration de la création de labs pour students/teachers/admins.
"""

from __future__ import annotations

import logging
from uuid import UUID

from labomatics.api.dto.auth import AuthUser
from labomatics.api.dto.notification import JobDTO
from labomatics.constants.enums import EventType, OwnerRole
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
        teacher_cohorts = await teacher_repo.list_by_teacher(UUID(user.subject))
        if teacher_cohorts:
            logger.info(f"User {user.username} resolved as TEACHER")
            return OwnerRole.TEACHER, None

        # Sinon Admin (pas de vérification supplémentaire, Keycloak le gère)
        logger.info(f"User {user.username} resolved as ADMIN")
        return OwnerRole.ADMIN, None

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
            Aucune exception levée (best-effort enqueue).
        """
        owner_role, student = await self._resolve_owner(user)

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

        lab_tasks.create_lab.delay(
            owner_keycloak_id=user.subject,
            owner_role=str(owner_role),
            owner_username=user.username,
            owner_email=user.email,
            student_id=str(student.id) if student else None,
            cluster_id=cluster_id_str,
            access_origin=access_origin,
            job_id=job_id,
        )

        return JobDTO(jobId=job_id)
