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
        self,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
        cohort_ids: list[UUID] | None = None,
    ) -> tuple[list[Student], int]:
        """Liste les étudiants avec pagination, recherche textuelle et filtre cohort.

        `cohort_ids`, s'il est fourni, filtre sur les étudiants ayant un
        enrollment actif (dates courantes) dans l'une de ces cohorts. Le
        filtre est appliqué en SQL (avant la pagination et dans le count),
        contrairement à l'ancien filtre `cohort` appliqué en Python par
        `StudentService.list_students` *après* le LIMIT/OFFSET — ce qui
        rendait `total_count` et le nombre d'items par page incohérents dès
        qu'un filtre cohort était actif.
        """
        from datetime import datetime

        from sqlalchemy import func, or_
        from sqlalchemy.orm import selectinload

        from labomatics.core.db.models import (
            Enrollment,
            LabProvisioning,
        )

        async with async_session_local() as session:

            def _apply_filters(s):
                if search:
                    search_lower = search.lower()
                    s = s.where(
                        or_(
                            self.model.first_name.ilike(f"%{search_lower}%"),
                            self.model.last_name.ilike(f"%{search_lower}%"),
                            self.model.email.ilike(f"%{search_lower}%"),
                            self.model.login.ilike(f"%{search_lower}%"),
                        )
                    )
                if cohort_ids:
                    now = datetime.now()
                    s = s.join(
                        Enrollment, Enrollment.student_id == self.model.id
                    ).where(
                        Enrollment.cohort_id.in_(cohort_ids),
                        Enrollment.start_date <= now,
                        (Enrollment.end_date.is_(None)) | (Enrollment.end_date >= now),
                    )
                return s

            stmt = _apply_filters(select(self.model).where(self.model.is_active))
            stmt = (
                stmt.options(
                    selectinload(self.model.enrollments).selectinload(
                        Enrollment.cohort
                    ),
                    selectinload(self.model.lab_provisioning).selectinload(
                        LabProvisioning.ip_allocation
                    ),
                    selectinload(self.model.lab_provisioning).selectinload(
                        LabProvisioning.vxlan_allocation
                    ),
                )
                .order_by(self.model.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
            )
            if cohort_ids:
                stmt = stmt.distinct()

            result = await session.execute(stmt)
            students = result.scalars().unique().all()

            count_stmt = _apply_filters(
                select(func.count(func.distinct(self.model.id))).where(
                    self.model.is_active
                )
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            return students, total

    async def get_by_id_with_enrollments(self, student_id: UUID) -> Student | None:
        """Récupère un étudiant avec ses enrollments et cohorts."""
        from sqlalchemy.orm import selectinload

        from labomatics.core.db.models import Enrollment

        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.id == student_id)
                .options(
                    selectinload(self.model.enrollments).selectinload(Enrollment.cohort)
                )
            )
            result = await session.execute(stmt)
            return result.scalars().unique().one_or_none()

    async def get_by_id_for_lab(self, student_id: UUID) -> Student | None:
        """Récupère un étudiant avec toutes les relations pour afficher le lab."""
        from sqlalchemy.orm import selectinload

        from labomatics.core.db.models import (
            Cluster,
            Enrollment,
            LabProvisioning,
        )

        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.id == student_id)
                .options(
                    selectinload(self.model.enrollments).selectinload(
                        Enrollment.cohort
                    ),
                    selectinload(self.model.lab_provisioning).selectinload(
                        LabProvisioning.ip_allocation
                    ),
                    selectinload(self.model.lab_provisioning).selectinload(
                        LabProvisioning.vxlan_allocation
                    ),
                    selectinload(self.model.lab_provisioning).selectinload(
                        LabProvisioning.vms
                    ),
                    selectinload(self.model.lab_provisioning)
                    .selectinload(LabProvisioning.cluster)
                    .selectinload(Cluster.credential),
                )
            )
            result = await session.execute(stmt)
            return result.scalars().unique().one_or_none()
