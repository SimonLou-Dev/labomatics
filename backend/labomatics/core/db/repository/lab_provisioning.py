"""Repository pour LabProvisioning."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from labomatics.core.db.models import LabProvisioning
from labomatics.core.db.models.cluster import Cluster
from labomatics.core.db.models.cohort import Cohort
from labomatics.core.db.models.enrollment import Enrollment
from labomatics.core.db.models.student import Student
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local

_ACTIVE_STATUSES = ("provisioning", "active")


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

    async def exists_active_for_cohort_cluster(
        self, cohort_id: UUID, cluster_id: UUID
    ) -> bool:
        """Vérifie si un étudiant de la cohort a un lab provisioning/actif sur ce cluster.

        Utilisé pour verrouiller le retrait d'un cluster assigné à une cohort
        tant que des étudiants l'utilisent encore (#53). La cohort doit être
        dans sa fenêtre de dates actuelle (`Cohort.start_date`/`end_date`) —
        une cohort dont l'année scolaire est terminée ne bloque plus le
        retrait, même si une ligne `LabProvisioning` reste encore active.
        """
        async with async_session_local() as session:
            now = datetime.now()
            stmt = (
                select(self.model.id)
                .join(Student, self.model.student_id == Student.id)
                .join(Enrollment, Enrollment.student_id == Student.id)
                .join(Cohort, Enrollment.cohort_id == Cohort.id)
                .where(
                    Enrollment.cohort_id == cohort_id,
                    Cohort.start_date <= now,
                    Cohort.end_date >= now,
                    self.model.cluster_id == cluster_id,
                    self.model.status.in_(_ACTIVE_STATUSES),
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def get_by_owner_keycloak_id(
        self, owner_keycloak_id: UUID
    ) -> LabProvisioning | None:
        """Récupère le lab provisioning le plus récent (non 'deleting') d'un owner.

        Utilisé pour résoudre "mon lab" pour un teacher/admin, qui n'a pas de
        `student_id` mais est identifié par son `owner_keycloak_id` (#58).
        """
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(
                    self.model.owner_keycloak_id == owner_keycloak_id,
                    self.model.status != "deleting",
                )
                .options(
                    selectinload(self.model.cluster),
                    selectinload(self.model.ip_allocation),
                    selectinload(self.model.vxlan_allocation),
                    selectinload(self.model.vms),
                )
                .order_by(self.model.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

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
