"""Repository pour StudentClusterExtra."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import StudentClusterExtra
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class StudentClusterExtraRepository(BaseRepository[StudentClusterExtra]):
    """Repository pour les accès additionnels étudiant → cluster."""

    def __init__(self) -> None:
        super().__init__(StudentClusterExtra)

    async def get_by_student_cluster(
        self, student_id: UUID, cluster_id: UUID
    ) -> StudentClusterExtra | None:
        """Récupère l'accès additionnel étudiant-cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.student_id == student_id)
                & (self.model.cluster_id == cluster_id)
                & (self.model.revoked_at is None)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[StudentClusterExtra]:
        """Liste les accès additionnels d'un étudiant."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.student_id == student_id) & (self.model.revoked_at is None)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[StudentClusterExtra]:
        """Liste les accès additionnels d'un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.cluster_id == cluster_id) & (self.model.revoked_at is None)
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_active(self) -> list[StudentClusterExtra]:
        """Liste tous les accès additionnels actifs."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.revoked_at is None)
            result = await session.execute(stmt)
            return result.scalars().all()
