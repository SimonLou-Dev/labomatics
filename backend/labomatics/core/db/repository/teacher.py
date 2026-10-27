"""Repository pour Teacher."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select

from labomatics.core.db.models import Teacher
from labomatics.core.db.repository.base import BaseRepository
from labomatics.core.db.session import async_session_local


class TeacherRepository(BaseRepository[Teacher]):
    """Repository pour les professeurs."""

    def __init__(self) -> None:
        super().__init__(Teacher)

    async def get_by_login(self, login: str) -> Teacher | None:
        """Récupère un professeur par son login."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.login == login)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Teacher | None:
        """Récupère un professeur par son email."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.email == email)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_by_keycloak_id(self, keycloak_id: UUID) -> Teacher | None:
        """Récupère un professeur par son ID Keycloak."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.keycloak_user_id == keycloak_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_with_pagination(
        self, page: int = 1, size: int = 20, search: str | None = None
    ) -> tuple[list[Teacher], int]:
        """Liste les professeurs actifs avec pagination et recherche textuelle."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.is_active)
            count_stmt = select(func.count(self.model.id)).where(self.model.is_active)

            if search:
                search_lower = search.lower()
                search_filter = or_(
                    self.model.first_name.ilike(f"%{search_lower}%"),
                    self.model.last_name.ilike(f"%{search_lower}%"),
                    self.model.email.ilike(f"%{search_lower}%"),
                    self.model.login.ilike(f"%{search_lower}%"),
                )
                stmt = stmt.where(search_filter)
                count_stmt = count_stmt.where(search_filter)

            stmt = (
                stmt.order_by(self.model.created_at.desc())
                .offset((page - 1) * size)
                .limit(size)
            )

            result = await session.execute(stmt)
            teachers = result.scalars().all()

            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            return teachers, total
