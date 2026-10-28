"""Repository pour TeacherCohort."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from labomatics.core.db.models import TeacherCohort
from labomatics.core.db.models.teacher import Teacher
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class TeacherCohortRepository(BaseRepository[TeacherCohort]):
    """Repository pour les associations professeur ↔ promo."""

    def __init__(self) -> None:
        super().__init__(TeacherCohort)

    async def get_by_teacher_cohort(
        self, teacher_id: UUID, cohort_id: UUID
    ) -> TeacherCohort | None:
        """Récupère l'association professeur-promo."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.teacher_id == teacher_id)
                & (self.model.cohort_id == cohort_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_teacher_id(self, teacher_id: UUID) -> list[TeacherCohort]:
        """Liste les promos d'un professeur (par son id applicatif)."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.teacher_id == teacher_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_teacher_keycloak_id(
        self, teacher_keycloak_id: UUID
    ) -> list[TeacherCohort]:
        """Liste les promos d'un professeur, résolu par son ID Keycloak (JWT).

        Utilisé par la résolution de rôle à la création de lab, qui ne connaît
        que l'UUID Keycloak de l'appelant (#58).
        """
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .join(Teacher, self.model.teacher_id == Teacher.id)
                .where(Teacher.keycloak_user_id == teacher_keycloak_id)
                .options(selectinload(self.model.cohort))
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cohort(self, cohort_id: UUID) -> list[TeacherCohort]:
        """Liste les professeurs d'une promo."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cohort_id == cohort_id)
            result = await session.execute(stmt)
            return result.scalars().all()
