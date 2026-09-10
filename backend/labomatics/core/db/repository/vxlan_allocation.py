"""Repository pour VxlanAllocation."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from labomatics.core.db.models import VxlanAllocation
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class VxlanAllocationRepository(BaseRepository[VxlanAllocation]):
    """Repository pour les allocations de VNI aux étudiants."""

    def __init__(self) -> None:
        super().__init__(VxlanAllocation)

    async def get_active_for_student(
        self, student_id: UUID, vxlan_range_cluster_id: UUID
    ) -> VxlanAllocation | None:
        """Récupère l'allocation VXLAN active d'un étudiant sur une plage/cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.student_id == student_id)
                & (self.model.vxlan_range_cluster_id == vxlan_range_cluster_id)
                & (self.model.released_at is None)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[VxlanAllocation]:
        """Liste toutes les allocations VXLAN d'un étudiant."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.student_id == student_id)
                .order_by(self.model.allocated_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_released(self) -> list[VxlanAllocation]:
        """Liste les allocations VXLAN libérées."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.released_at is not None)
                .order_by(self.model.released_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[VxlanAllocation]:
        """Liste les allocations VXLAN actives d'un cluster."""
        async with async_session_local() as session:
            from sqlalchemy.orm import selectinload

            from labomatics.core.db.models import VxlanRangeCluster

            # Get all vxlan_range_cluster IDs for this cluster
            range_cluster_stmt = select(VxlanRangeCluster.id).where(
                VxlanRangeCluster.cluster_id == cluster_id
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
                    (self.model.vxlan_range_cluster_id.in_(range_cluster_ids))
                    & (self.model.released_at.is_(None))
                )
            )
            result = await session.execute(stmt)
            return result.scalars().unique().all()

    async def list_by_vxlan_range(self, vxlan_range_id: UUID) -> list[VxlanAllocation]:
        """Liste les allocations VXLAN actives d'une plage VXLAN (tous les clusters)."""
        async with async_session_local() as session:
            from sqlalchemy.orm import selectinload

            from labomatics.core.db.models import VxlanRangeCluster

            # Get all vxlan_range_cluster IDs for this range
            range_cluster_stmt = select(VxlanRangeCluster.id).where(
                VxlanRangeCluster.vxlan_range_id == vxlan_range_id
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
                    (self.model.vxlan_range_cluster_id.in_(range_cluster_ids))
                    & (self.model.released_at.is_(None))
                )
                .order_by(self.model.allocated_at)
            )
            result = await session.execute(stmt)
            return result.scalars().unique().all()
