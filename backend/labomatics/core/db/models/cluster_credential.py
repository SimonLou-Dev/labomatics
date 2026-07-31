from uuid import UUID

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import BYTEA, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ClusterCredential(Base, UUIDPkMixin, TimestampMixin):
    """Token API Proxmox chiffré au repos."""

    __tablename__ = "cluster_credential"

    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
        unique=True,
    )
    token_id: Mapped[str] = mapped_column(
        comment="Token ID (format: user@realm!token-name), clair",
    )
    encrypted_token_secret: Mapped[bytes] = mapped_column(
        BYTEA,
        comment="Secret chiffré en Fernet",
    )
    encryption_key_version: Mapped[int] = mapped_column(
        default=1,
        comment="Version de clé pour rotation",
    )
    quota_config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Config future pour quotas par cluster",
    )

    # Relationships
    cluster: Mapped["Cluster"] = relationship(  # type: ignore
        back_populates="credential",
    )


# Forward references for circular imports
from backend.labomatics.core.db.models.cluster import Cluster  # noqa: E402
