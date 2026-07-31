"""Repository pour Enrollment."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import Enrollment
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class EnrollmentRepository(BaseRepository[Enrollment]):
    """Repository pour les affectations étudiant → promo."""

    def __init__(self) -> None:
        super().__init__(Enrollment)

    async def get_active_for_student(self, student_id: UUID) -> Enrollment | None:
        """Récupère l'affectation active d'un étudiant (end_date IS NULL)."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.student_id == student_id) & (self.model.end_date is None)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[Enrollment]:
        """Liste l'historique d'affectations d'un étudiant."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.student_id == student_id)
                .order_by(self.model.start_date.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cohort(self, cohort_id: UUID) -> list[Enrollment]:
        """Liste les affectations d'une promo."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cohort_id == cohort_id)
            result = await session.execute(stmt)
            return result.scalars().all()
