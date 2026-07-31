"""Repository pour VxlanRange."""

from __future__ import annotations

from backend.labomatics.core.db.models import VxlanRange
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class VxlanRangeRepository(BaseRepository[VxlanRange]):
    """Repository pour les plages VNI VXLAN."""

    def __init__(self) -> None:
        super().__init__(VxlanRange)

    async def get_by_name(self, name: str) -> VxlanRange | None:
        """Récupère une plage VXLAN par son nom."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.name == name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_all(self) -> list[VxlanRange]:
        """Liste toutes les plages VXLAN."""
        async with async_session_local() as session:
            stmt = select(self.model)
            result = await session.execute(stmt)
            return result.scalars().all()
