"""Repository pour IpAllocation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from labomatics.core.db.models import IpAllocation
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class IpAllocationRepository(BaseRepository[IpAllocation]):
    """Repository pour les allocations d'IP publiques aux étudiants."""

    def __init__(self) -> None:
        super().__init__(IpAllocation)

    async def get_active_for_student(
        self, student_id: UUID, ip_range_cluster_id: UUID
    ) -> IpAllocation | None:
        """Récupère l'allocation IP active d'un étudiant sur une plage/cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.student_id == student_id)
                & (self.model.ip_range_cluster_id == ip_range_cluster_id)
                & (self.model.released_at is None)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[IpAllocation]:
        """Liste toutes les allocations IP d'un étudiant."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.student_id == student_id)
                .order_by(self.model.allocated_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_released(self) -> list[IpAllocation]:
        """Liste les allocations IP libérées."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.released_at is not None)
                .order_by(self.model.released_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[IpAllocation]:
        """Liste les allocations IP actives d'un cluster."""
        async with async_session_local() as session:
            from sqlalchemy.orm import selectinload

            from labomatics.core.db.models import IpRangeCluster

            # Get all ip_range_cluster IDs for this cluster
            range_cluster_stmt = select(IpRangeCluster.id).where(
                IpRangeCluster.cluster_id == cluster_id
            )
            range_cluster_result = await session.execute(range_cluster_stmt)
            range_cluster_ids = [row[0] for row in range_cluster_result.all()]

            if not range_cluster_ids:
                return []

            # Get all active allocations for these range_clusters
            stmt = (
                select(self.model)
                .options(selectinload(self.model.student))
                .where(
                    (self.model.ip_range_cluster_id.in_(range_cluster_ids))
                    & (self.model.released_at.is_(None))
                )
            )
            result = await session.execute(stmt)
            allocations = result.scalars().unique().all()
            return allocations

    async def list_by_ip_range(self, ip_range_id: UUID) -> list[IpAllocation]:
        """Liste les allocations IP actives d'une plage IP (tous les clusters)."""
        async with async_session_local() as session:
            from sqlalchemy.orm import selectinload

            from labomatics.core.db.models import IpRangeCluster

            # Get all ip_range_cluster IDs for this range
            range_cluster_stmt = select(IpRangeCluster.id).where(
                IpRangeCluster.ip_range_id == ip_range_id
            )
            range_cluster_result = await session.execute(range_cluster_stmt)
            range_cluster_ids = [row[0] for row in range_cluster_result.all()]

            if not range_cluster_ids:
                return []

            # Get all active allocations for these range_clusters
            stmt = (
                select(self.model)
                .options(selectinload(self.model.student))
                .where(
                    (self.model.ip_range_cluster_id.in_(range_cluster_ids))
                    & (self.model.released_at.is_(None))
                )
                .order_by(self.model.allocated_at)
            )
            result = await session.execute(stmt)
            return result.scalars().unique().all()
