"""Repository pour IpRangeCluster."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from labomatics.core.db.models import IpRangeCluster
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class IpRangeClusterRepository(BaseRepository[IpRangeCluster]):
    """Repository pour les associations plage IP ↔ cluster."""

    def __init__(self) -> None:
        super().__init__(IpRangeCluster)

    async def get_by_range_cluster(
        self, ip_range_id: UUID, cluster_id: UUID
    ) -> IpRangeCluster | None:
        """Récupère l'association plage IP-cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.ip_range_id == ip_range_id)
                & (self.model.cluster_id == cluster_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_range(self, ip_range_id: UUID) -> list[IpRangeCluster]:
        """Liste les clusters d'une plage IP."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.ip_range_id == ip_range_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[IpRangeCluster]:
        """Liste les plages IP d'un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cluster_id == cluster_id)
            result = await session.execute(stmt)
            return result.scalars().all()
