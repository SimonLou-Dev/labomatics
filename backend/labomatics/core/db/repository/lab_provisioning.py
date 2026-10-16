"""Repository pour LabProvisioning."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from labomatics.core.db.models import LabProvisioning
from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class LabProvisioningRepository(BaseRepository[LabProvisioning]):
    """Repository pour l'état de provisioning du lab personnel par étudiant/cluster."""

    def __init__(self) -> None:
        super().__init__(LabProvisioning)

    async def get_by_student_cluster(
        self, student_id: UUID, cluster_id: UUID
    ) -> LabProvisioning | None:
        """Récupère l'état de provisioning pour un étudiant sur un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(
                (self.model.student_id == student_id)
                & (self.model.cluster_id == cluster_id)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_by_student(self, student_id: UUID) -> list[LabProvisioning]:
        """Liste les états de provisioning d'un étudiant."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.student_id == student_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_id: UUID) -> list[LabProvisioning]:
        """Liste les états de provisioning d'un cluster."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cluster_id == cluster_id)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_status(self, status: str) -> list[LabProvisioning]:
        """Liste les provisionings avec un statut donné."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.status == status)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_active_with_cluster_and_ip(self) -> list[LabProvisioning]:
        """Labs actifs, avec cluster (+ credential) et allocation IP pré-chargés.

        Utilisé par la tâche quotidienne de contrôle/remédiation réseau (#61),
        qui a besoin de se connecter au cluster Proxmox de chaque lab et de
        connaître l'IP WAN allouée sans requête supplémentaire.
        """
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.status == "active")
                .options(
                    selectinload(self.model.cluster).selectinload(Cluster.credential),
                    selectinload(self.model.student),
                    selectinload(self.model.ip_allocation),
                )
            )
            result = await session.execute(stmt)
            return result.scalars().all()
