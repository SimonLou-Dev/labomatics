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
            from labomatics.core.db.models import IpRangeCluster

            stmt = (
                select(self.model)
                .join(IpRangeCluster)
                .where(
                    (self.model.ip_range_cluster_id == IpRangeCluster.id)
                    & (IpRangeCluster.cluster_id == cluster_id)
                    & (self.model.released_at is None)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_ip_range(self, ip_range_id: UUID) -> list[IpAllocation]:
        """Liste les allocations IP d'une plage IP (tous les clusters)."""
        async with async_session_local() as session:
            from sqlalchemy.orm import selectinload

            from labomatics.core.db.models import IpRangeCluster

            stmt = (
                select(self.model)
                .join(IpRangeCluster)
                .options(selectinload(self.model.student))
                .where(
                    (self.model.ip_range_cluster_id == IpRangeCluster.id)
                    & (IpRangeCluster.ip_range_id == ip_range_id)
                    & (self.model.released_at is None)
                )
                .order_by(self.model.allocated_at)
            )
            result = await session.execute(stmt)
            return result.scalars().all()
