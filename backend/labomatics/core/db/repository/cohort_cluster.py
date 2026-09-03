"""Repository pour CohortCluster."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from labomatics.core.db.models import CohortCluster
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class CohortClusterRepository(BaseRepository[CohortCluster]):
    """Repository pour les associations promo ↔ cluster."""

    def __init__(self) -> None:
        super().__init__(CohortCluster)

    async def get_by_cohort_cluster(
        self, cohort_id: UUID, cluster_id: UUID
    ) -> CohortCluster | None:
        """Récupère l'association cohort-cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.cohort_id == cohort_id)
                & (self.model.cluster_id == cluster_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_cohort(self, cohort_id: UUID) -> list[CohortCluster]:
        """Liste les clusters d'une promo."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.cohort_id == cohort_id)
                .options(selectinload(self.model.cluster))
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[CohortCluster]:
        """Liste les promos d'un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cluster_id == cluster_id)
            result = await session.execute(stmt)
            return result.scalars().all()
