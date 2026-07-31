from datetime import datetime
from uuid import UUID

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import UUIDPkMixin
from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column


class AuditLog(Base, UUIDPkMixin):
    """Piste d'audit des actions sensibles."""

    __tablename__ = "audit_log"

    actor_keycloak_id: Mapped[UUID] = mapped_column(
        comment="Keycloak sub de l'acteur",
    )
    actor_role: Mapped[str] = mapped_column(
        comment="Rôle: student|teacher|admin|system",
    )
    action: Mapped[str] = mapped_column(
        comment="Action: lab.destroy, token.regenerate, etc.",
    )
    resource_type: Mapped[str]
    resource_id: Mapped[UUID | None] = None
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
    )

    __table_args__ = (
        Index("idx_audit_log_resource", "resource_type", "resource_id"),
        Index("idx_audit_log_actor", "actor_keycloak_id", "created_at"),
    )
