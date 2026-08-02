from datetime import datetime

from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import UUIDPkMixin


class AuditLog(Base, UUIDPkMixin):
    """Piste d'audit des actions sensibles."""

    __tablename__ = "audit_log"

    actor_keycloak_id: Mapped[str] = mapped_column()
    actor_role: Mapped[str] = mapped_column()
    action: Mapped[str] = mapped_column()
    resource_type: Mapped[str] = mapped_column()
    resource_id: Mapped[str | None] = mapped_column(
        nullable=True,
    )
    details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )

    __table_args__ = (
        Index("idx_audit_log_resource", "resource_type", "resource_id"),
        Index("idx_audit_log_actor", "actor_keycloak_id", "created_at"),
    )
