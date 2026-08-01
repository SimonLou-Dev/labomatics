"""Repository pour IpRange."""

from __future__ import annotations

from sqlalchemy import select

from labomatics.core.db.models import IpRange
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class IpRangeRepository(BaseRepository[IpRange]):
    """Repository pour les plages IP publiques WAN."""

    def __init__(self) -> None:
        super().__init__(IpRange)

    async def get_by_name(self, name: str) -> IpRange | None:
        """Récupère une plage IP par son nom."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.name == name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_all(self) -> list[IpRange]:
        """Liste toutes les plages IP."""
        async with async_session_local() as session:
            stmt = select(self.model)
            result = await session.execute(stmt)
            return result.scalars().all()
