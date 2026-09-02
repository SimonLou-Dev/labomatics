from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import BYTEA, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class ClusterCredential(Base, UUIDPkMixin, TimestampMixin):
    """Token API Proxmox chiffré au repos."""

    __tablename__ = "cluster_credential"

    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
        unique=True,
    )
    user: Mapped[str] = mapped_column()
    token_id: Mapped[str] = mapped_column()
    encrypted_token_secret: Mapped[bytes] = mapped_column(
        BYTEA,
    )
    encryption_key_version: Mapped[int] = mapped_column(
        default=1,
    )
    quota_config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    cluster: Mapped["Cluster"] = relationship(  # type: ignore
        back_populates="credential",
    )


# Forward references for circular imports
from labomatics.core.db.models.cluster import Cluster  # noqa: E402
