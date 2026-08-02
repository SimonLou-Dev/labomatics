"""Repository pour Student."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from labomatics.core.db.models import Student
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class StudentRepository(BaseRepository[Student]):
    """Repository pour les étudiants."""

    def __init__(self) -> None:
        super().__init__(Student)

    async def get_by_external_id(self, external_id: int) -> Student | None:
        """Récupère un étudiant par son ID ESGI externe."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.external_id == external_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_login(self, login: str) -> Student | None:
        """Récupère un étudiant par son login."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.login == login)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Student | None:
        """Récupère un étudiant par son email."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.email == email)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_keycloak_id(self, keycloak_id: UUID) -> Student | None:
        """Récupère un étudiant par son ID Keycloak."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.keycloak_user_id == keycloak_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_active(self) -> list[Student]:
        """Liste les étudiants actifs."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.is_active)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_with_pagination(
        self, page: int = 1, size: int = 20
    ) -> tuple[list[Student], int]:
        """Liste les étudiants avec pagination (jointure SQL simple)."""
        from sqlalchemy import func, join, outerjoin
        from sqlalchemy.orm import contains_eager

        from labomatics.core.db.models import (
            Cohort,
            Enrollment,
            IpAllocation,
            LabProvisioning,
            VxlanAllocation,
        )

        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.is_active)
                .outerjoin(Enrollment, Enrollment.student_id == self.model.id)
                .outerjoin(Cohort, Cohort.id == Enrollment.cohort_id)
                .outerjoin(
                    LabProvisioning, LabProvisioning.student_id == self.model.id
                )
                .outerjoin(
                    IpAllocation, IpAllocation.id == LabProvisioning.ip_allocation_id
                )
                .outerjoin(
                    VxlanAllocation,
                    VxlanAllocation.id == LabProvisioning.vxlan_allocation_id,
                )
                .distinct()
                .order_by(self.model.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
            )

            result = await session.execute(stmt)
            students = result.scalars().unique().all()

            count_stmt = select(func.count(self.model.id)).where(
                self.model.is_active
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            return students, total
