"""Repository pour Cohort."""

from __future__ import annotations

from backend.labomatics.core.db.models import Cohort
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class CohortRepository(BaseRepository[Cohort]):
    """Repository pour les promos."""

    def __init__(self) -> None:
        super().__init__(Cohort)

    async def get_by_name_year(self, name: str, year: int) -> Cohort | None:
        """Récupère une promo par nom et année."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.name == name) & (self.model.year == year)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_active(self) -> list[Cohort]:
        """Liste les promos actives."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.is_active)
            result = await session.execute(stmt)
            return result.scalars().all()
