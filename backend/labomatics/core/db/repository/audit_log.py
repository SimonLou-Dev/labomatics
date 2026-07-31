"""Repository pour AuditLog."""

from __future__ import annotations

from uuid import UUID

from backend.labomatics.core.db.models import AuditLog
from backend.labomatics.core.db.repository.base import BaseRepository
from backend.labomatics.core.db.session import async_session_local
from sqlalchemy import select


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository pour la piste d'audit des actions sensibles."""

    def __init__(self) -> None:
        super().__init__(AuditLog)

    async def list_by_actor(self, actor_keycloak_id: UUID) -> list[AuditLog]:
        """Liste les actions d'un acteur."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.actor_keycloak_id == actor_keycloak_id)
                .order_by(self.model.created_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_resource(
        self, resource_type: str, resource_id: UUID | None = None
    ) -> list[AuditLog]:
        """Liste les actions sur une ressource."""
        async with async_session_local() as session:
            stmt = select(self.model).where(self.model.resource_type == resource_type)
            if resource_id is not None:
                stmt = stmt.where(self.model.resource_id == resource_id)
            stmt = stmt.order_by(self.model.created_at.desc())
            result = await session.execute(stmt)
            return result.scalars().all()

    async def list_by_action(self, action: str) -> list[AuditLog]:
        """Liste les actions d'un certain type."""
        async with async_session_local() as session:
            stmt = (
                select(self.model)
                .where(self.model.action == action)
                .order_by(self.model.created_at.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()
