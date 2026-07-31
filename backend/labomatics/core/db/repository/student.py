"""Repository pour Student."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import Student
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


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
