from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import CIDR, INET, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class IpRange(Base, UUIDPkMixin, TimestampMixin):
    """Plage d'IP publiques WAN."""

    __tablename__ = "ip_range"

    name: Mapped[str] = mapped_column(
        default="default",
    )
    network: Mapped[str] = mapped_column(
        CIDR,
    )
    gateway: Mapped[str] = mapped_column(
        INET,
    )
    exclusions: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    range_clusters: Mapped[list["IpRangeCluster"]] = relationship(
        back_populates="ip_range",
    )

    __table_args__ = (UniqueConstraint("name"),)


# Forward references for circular imports
from labomatics.core.db.models.ip_range_cluster import (  # noqa: E402
    IpRangeCluster,
)
