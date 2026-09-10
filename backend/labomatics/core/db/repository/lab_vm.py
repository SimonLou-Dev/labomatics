"""Repository pour LabVm."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from labomatics.core.db.models import LabVm
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class LabVmRepository(BaseRepository[LabVm]):
    """Repository pour les VMs du lab personnel."""

    def __init__(self) -> None:
        super().__init__(LabVm)

    async def list_by_provisioning(self, provisioning_id: UUID) -> list[LabVm]:
        """Liste les VMs d'un lab provisioning.

        Parameters
        ----------
        provisioning_id : UUID
            Identifiant du LabProvisioning.

        Returns
        -------
        list[LabVm]
            Liste des VMs associées.

        """
        async with async_session_local() as session:
            stmt = select(self.model).where(
                self.model.lab_provisioning_id == provisioning_id
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_cluster(self, cluster_name: str) -> list[LabVm]:
        """Liste les VMs d'un cluster.

        Parameters
        ----------
        cluster_name : str
            Nom du cluster.

        Returns
        -------
        list[LabVm]
            Liste des VMs du cluster.

        """
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.cluster_name == cluster_name)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_state(self, state: str) -> list[LabVm]:
        """Liste les VMs avec un état donné.

        Parameters
        ----------
        state : str
            État de la VM (running, stopped, etc.).

        Returns
        -------
        list[LabVm]
            Liste des VMs dans cet état.

        """
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.state == state)
            result = await session.execute(stmt)
            return result.scalars().all()
