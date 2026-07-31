"""Repository pour VxlanAllocation."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import VxlanAllocation
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


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
            from backend.labomatics.core.db.models import VxlanRangeCluster

            stmt = (
                select(self.model)
                .join(VxlanRangeCluster)
                .where(
                    (self.model.vxlan_range_cluster_id == VxlanRangeCluster.id)
                    & (VxlanRangeCluster.cluster_id == cluster_id)
                    & (self.model.released_at is None)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()
