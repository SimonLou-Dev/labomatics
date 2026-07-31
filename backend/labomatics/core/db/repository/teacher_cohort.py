"""Repository pour TeacherCohort."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import TeacherCohort
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class TeacherCohortRepository(BaseRepository[TeacherCohort]):
    """Repository pour les associations enseignant (Keycloak) ↔ promo."""

    def __init__(self) -> None:
        super().__init__(TeacherCohort)

    async def get_by_teacher_cohort(
        self, teacher_keycloak_id: UUID, cohort_id: UUID
    ) -> TeacherCohort | None:
        """Récupère l'association enseignant-promo."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.teacher_keycloak_id == teacher_keycloak_id)
                & (self.model.cohort_id == cohort_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_teacher(self, teacher_keycloak_id: UUID) -> list[TeacherCohort]:
        """Liste les promos d'un enseignant."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                self.model.teacher_keycloak_id == teacher_keycloak_id
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cohort(self, cohort_id: UUID) -> list[TeacherCohort]:
        """Liste les enseignants d'une promo."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cohort_id == cohort_id)
            result = await session.execute(stmt)
            return result.scalars().all()
