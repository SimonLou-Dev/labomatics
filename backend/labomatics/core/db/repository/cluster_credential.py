"""Repository pour ClusterCredential."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import ClusterCredential
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import delete, select


class ClusterCredentialRepository(BaseRepository[ClusterCredential]):
    """Repository pour les credentials de cluster Proxmox."""

    def __init__(self) -> None:
        super().__init__(ClusterCredential)

    async def get_by_cluster_id(self, cluster_id: UUID) -> ClusterCredential | None:
        """Récupère la credential d'un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cluster_id == cluster_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def delete_by_cluster_id(self, cluster_id: UUID) -> bool:
        """Supprime la credential d'un cluster."""
        async with async_session_local() as session:
            stmt = delete(self.model).where(self.model.cluster_id == cluster_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
