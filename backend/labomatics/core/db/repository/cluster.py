"""Repository pour Cluster."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from labomatics.core.db.models import Cluster
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


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

    async def get_with_ranges(self, cluster_id: UUID) -> Cluster | None:
        """Récupère un cluster avec ses ranges IP et VXLAN et leurs relations imbriquées."""
        from labomatics.core.db.models import (
            IpRangeCluster,
            VxlanRangeCluster,
        )

        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.id == cluster_id)
                .options(
                    selectinload(self.model.credential),
                    selectinload(self.model.ip_range_clusters).selectinload(
                        IpRangeCluster.ip_range
                    ),
                    selectinload(self.model.vxlan_range_clusters).selectinload(
                        VxlanRangeCluster.vxlan_range
                    ),
                )
            )
            result = await session.execute(stmt)
            return result.scalars().unique().one_or_none()
