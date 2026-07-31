"""Repository pour Cluster."""

from __future__ import annotations

from backend.labomatics.core.db.models import Cluster
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class ClusterRepository(BaseRepository[Cluster]):
    """Repository pour les clusters Proxmox."""

    def __init__(self) -> None:
        super().__init__(Cluster)

    async def get_default(self) -> Cluster | None:
        """Récupère le cluster par défaut pour les nouvelles promos."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.is_default_for_new_cohorts)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Cluster | None:
        """Récupère un cluster par son nom."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.name == name)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_active(self) -> list[Cluster]:
        """Liste les clusters actifs."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.is_active)
            result = await session.execute(stmt)
            return result.scalars().all()
