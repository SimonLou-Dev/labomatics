"""Service pour les professeurs."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException

from labomatics.api.dto.student import StudentListResponseDTO
from labomatics.api.dto.teacher import (
    TeacherCreateDTO,
    TeacherListItemDTO,
    TeacherListResponseDTO,
    TeacherUpdateDTO,
)
from labomatics.core.config.settings import settings
from labomatics.core.db.models import Teacher, TeacherCohort
from labomatics.core.db.repository.cohort import CohortRepository
from labomatics.core.db.repository.teacher import TeacherRepository
from labomatics.core.db.repository.teacher_cohort import TeacherCohortRepository
from labomatics.services.email_templates import EmailType
from labomatics.utils.login_helper import generate_login, generate_password

logger = logging.getLogger(__name__)


class TeacherService:
    """Service pour la gestion des professeurs (#58)."""

    def __init__(
        self,
        repo: TeacherRepository | None = None,
        teacher_cohort_repo: TeacherCohortRepository | None = None,
        cohort_repo: CohortRepository | None = None,
        keycloak_service: object | None = None,
        mail_service: object | None = None,
    ) -> None:
        self.repo = repo or TeacherRepository()
        self.teacher_cohort_repo = teacher_cohort_repo or TeacherCohortRepository()
        self.cohort_repo = cohort_repo or CohortRepository()
        self.keycloak_service = keycloak_service
        self.mail_service = mail_service

    async def _ensure_cohorts_exist(self, cohort_ids: list[str]) -> list[UUID]:
        """Valide que chaque cohort_id existe. Lève 404 sinon.

        Contrairement à l'import CSV étudiant (tolérant aux données sales car
        rejoué périodiquement), un ajout de prof est une saisie admin directe
        via l'UI : une cohort_id invalide doit échouer immédiatement.
        """
        ids = [UUID(c) for c in cohort_ids]
        for cohort_id in ids:
            cohort = await self.cohort_repo.get(cohort_id)
            if not cohort:
                raise HTTPException(404, f"Cohort {cohort_id} not found")
        return ids

    async def _to_list_item(self, teacher: Teacher) -> TeacherListItemDTO:
        teacher_cohorts = await self.teacher_cohort_repo.list_by_teacher_id(teacher.id)
        cohort_names = []
        for tc in teacher_cohorts:
            # `tc.cohort` n'est pas eager-chargée par `list_by_teacher_id` : un
            # accès direct déclencherait un lazy-load hors de la session (déjà
            # fermée par le repository), donc on repasse par le repo.
            cohort = await self.cohort_repo.get(tc.cohort_id)
            if cohort:
                cohort_names.append(cohort.name)
        return TeacherListItemDTO(
            id=str(teacher.id),
            login=teacher.login,
            email=teacher.email,
            first_name=teacher.first_name,
            last_name=teacher.last_name,
            cohort_names=cohort_names,
            is_active=teacher.is_active,
        )

    async def list_teachers(
        self, page: int = 1, size: int = 20, search: str | None = None
    ) -> TeacherListResponseDTO:
        """Liste les professeurs actifs avec pagination et recherche textuelle."""
        teachers, total = await self.repo.list_with_pagination(
            page, size, search=search
        )
        items = [await self._to_list_item(t) for t in teachers]
        total_pages = (total + size - 1) // size
        return TeacherListResponseDTO(
            items=items,
            total_count=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    async def create_teacher(self, data: TeacherCreateDTO) -> TeacherListItemDTO:
        """Crée un professeur: DB + classes assignées + Keycloak + mail."""
        from labomatics.services.keycloak_service import KeycloakService
        from labomatics.services.mail_service import MailService

        cohort_ids = await self._ensure_cohorts_exist(data.cohort_ids)

        login = generate_login(data.first_name, data.last_name)
        teacher = Teacher(
            login=login,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            is_active=True,
        )
        teacher = await self.repo.add(teacher)
        logger.info(f"Teacher créé en DB: {login}")

        for cohort_id in cohort_ids:
            await self.teacher_cohort_repo.add(
                TeacherCohort(teacher_id=teacher.id, cohort_id=cohort_id)
            )

        # Contrairement à `StudentService.create_student`, on NE PAS avale
        # l'exception Keycloak ici : il n'existe pas de réimport périodique
        # qui réconcilierait un prof orphelin sans compte fonctionnel.
        keycloak_svc = self.keycloak_service or KeycloakService()
        await keycloak_svc.create_user(
            login=login,
            email=data.email,
            first_name=data.first_name,
            last_name=data.last_name,
        )
        await keycloak_svc.add_user_to_group(login=login, group_name="prof")

        password = generate_password()
        await keycloak_svc.set_user_password(
            login=login, password=password, temporary=True
        )

        cohorts = [await self.cohort_repo.get(c) for c in cohort_ids]
        cohort_names = [c.name for c in cohorts if c]

        mail_svc = self.mail_service or MailService()
        await mail_svc.send_templated_mail(
            to=data.email,
            subject=f"Labomatics ESGI Reims - Accès professeur - {data.first_name} {data.last_name}",
            email_type=EmailType.TEACHER_ENROLLMENT,
            context={
                "teacher_name": data.first_name,
                "cohort_names": cohort_names,
                "login": login,
                "email": data.email,
                "password": password,
                "portal_url": settings.front_url,
            },
        )
        logger.info(f"Mail d'accès prof envoyé à {data.email}")

        return await self._to_list_item(teacher)

    async def update_teacher(
        self, teacher_id: UUID, data: TeacherUpdateDTO
    ) -> TeacherListItemDTO:
        """Met à jour le profil et les classes assignées d'un professeur."""
        from labomatics.services.keycloak_service import KeycloakService

        teacher = await self.repo.get(teacher_id)
        if not teacher:
            raise HTTPException(404, "Teacher not found")

        new_cohort_ids = set(await self._ensure_cohorts_exist(data.cohort_ids))
        old_email = teacher.email

        await self.repo.update(
            teacher_id,
            {
                "first_name": data.first_name,
                "last_name": data.last_name,
                "email": data.email,
            },
        )

        if old_email != data.email:
            keycloak_svc = self.keycloak_service or KeycloakService()
            await keycloak_svc.update_user(
                login=teacher.login,
                email=data.email,
                first_name=data.first_name,
                last_name=data.last_name,
            )

        existing = await self.teacher_cohort_repo.list_by_teacher_id(teacher_id)
        existing_cohort_ids = {tc.cohort_id for tc in existing}

        for tc in existing:
            if tc.cohort_id not in new_cohort_ids:
                await self.teacher_cohort_repo.delete(tc.id)

        for cohort_id in new_cohort_ids - existing_cohort_ids:
            await self.teacher_cohort_repo.add(
                TeacherCohort(teacher_id=teacher_id, cohort_id=cohort_id)
            )

        teacher = await self.repo.get(teacher_id)
        return await self._to_list_item(teacher)

    async def delete_teacher(self, teacher_id: UUID) -> None:
        """Désactive un professeur: DB + suppression du compte Keycloak.

        Ne nettoie pas les ressources Proxmox (pool/VM) d'un éventuel lab
        personnel du professeur — contrairement à la suppression étudiant,
        qui a une tâche Celery dédiée pour ça. Hors scope de #58 : un prof
        désactivé garde son lab existant jusqu'à nettoyage manuel.
        """
        from labomatics.services.keycloak_service import KeycloakService

        teacher = await self.repo.get(teacher_id)
        if not teacher:
            raise HTTPException(404, "Teacher not found")

        await self.repo.update(teacher_id, {"is_active": False})

        keycloak_svc = self.keycloak_service or KeycloakService()
        try:
            await keycloak_svc.delete_user(login=teacher.login)
        except Exception as e:
            logger.error(f"Erreur suppression Keycloak pour {teacher.login}: {e}")

    async def list_students_for_teacher(
        self,
        teacher_keycloak_id: UUID,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
    ) -> StudentListResponseDTO:
        """Liste les élèves des classes assignées à ce professeur (#58).

        Retourne une page vide (pas une erreur) si le professeur n'a aucune
        classe assignée.
        """
        from labomatics.services.student_service import StudentService

        teacher_cohorts = await self.teacher_cohort_repo.list_by_teacher_keycloak_id(
            teacher_keycloak_id
        )
        cohort_ids = [tc.cohort_id for tc in teacher_cohorts]

        student_svc = StudentService()
        return await student_svc.list_students(
            page=page, size=size, search=search, cohort_ids=cohort_ids
        )
