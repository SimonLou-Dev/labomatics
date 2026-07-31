from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import CIDR, INET, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship


class IpRange(Base, UUIDPkMixin, TimestampMixin):
    """Plage d'IP publiques WAN."""

    __tablename__ = "ip_range"

    name: Mapped[str] = mapped_column(
        default="default",
    )
    network: Mapped[str] = mapped_column(
        CIDR,
        comment="Réseau (ex. 172.16.0.0/24)",
    )
    gateway: Mapped[str] = mapped_column(
        INET,
    )
    exclusions: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Liste de CIDR à exclure",
    )

    # Relationships
    range_clusters: Mapped[list["IpRangeCluster"]] = relationship(
        back_populates="ip_range",
    )
    allocations: Mapped[list["IpAllocation"]] = relationship(
        back_populates="ip_range",
    )

    __table_args__ = (UniqueConstraint("name"),)


# Forward references for circular imports
from backend.labomatics.core.db.models.ip_allocation import (  # noqa: E402
    IpAllocation,
)
from backend.labomatics.core.db.models.ip_range_cluster import (  # noqa: E402
    IpRangeCluster,
)
