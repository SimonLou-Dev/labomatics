"""Repository pour Enrollment."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from labomatics.core.db.models import Enrollment
from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class EnrollmentRepository(BaseRepository[Enrollment]):
    """Repository pour les affectations étudiant → promo."""

    def __init__(self) -> None:
        super().__init__(Enrollment)

    async def get_active_for_student(self, student_id: UUID) -> Enrollment | None:
        """Récupère l'affectation active d'un étudiant (dont la cohort est dans sa fenêtre de dates)."""
        async with async_session_local() as session:
            now = datetime.now()
            stmt = (
                select(self.model)
                .join(Cohort, self.model.cohort_id == Cohort.id)
                .where(
                    self.model.student_id == student_id,
                    Cohort.start_date <= now,
                    Cohort.end_date >= now,
                )
            )
            result = await session.execute(stmt)
            return result.scalars().first()

    async def list_by_student(self, student_id: UUID) -> list[Enrollment]:
        """Liste l'historique d'affectations d'un étudiant."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.student_id == student_id)
                .options(selectinload(self.model.cohort))
                .order_by(self.model.created_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cohort(self, cohort_id: UUID) -> list[Enrollment]:
        """Liste les affectations d'une promo."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cohort_id == cohort_id)
            result = await session.execute(stmt)
            return result.scalars().all()
