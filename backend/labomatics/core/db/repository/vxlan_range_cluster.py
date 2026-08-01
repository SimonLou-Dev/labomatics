"""Repository pour VxlanRangeCluster."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from labomatics.core.db.models import VxlanRangeCluster
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class VxlanRangeClusterRepository(BaseRepository[VxlanRangeCluster]):
    """Repository pour les associations plage VXLAN ↔ cluster."""

    def __init__(self) -> None:
        super().__init__(VxlanRangeCluster)

    async def get_by_range_cluster(
        self, vxlan_range_id: UUID, cluster_id: UUID
    ) -> VxlanRangeCluster | None:
        """Récupère l'association plage VXLAN-cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.vxlan_range_id == vxlan_range_id)
                & (self.model.cluster_id == cluster_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_range(self, vxlan_range_id: UUID) -> list[VxlanRangeCluster]:
        """Liste les clusters d'une plage VXLAN."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.vxlan_range_id == vxlan_range_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[VxlanRangeCluster]:
        """Liste les plages VXLAN d'un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cluster_id == cluster_id)
            result = await session.execute(stmt)
            return result.scalars().all()
