from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import CIDR, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class VxlanRange(Base, UUIDPkMixin, TimestampMixin):
    """Plage de VNI VXLAN."""

    __tablename__ = "vxlan_range"

    name: Mapped[str] = mapped_column(
        default="default",
    )
    vni_min: Mapped[int]
    vni_max: Mapped[int]
    base_network: Mapped[str] = mapped_column(
        CIDR,
    )
    exclusions: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    range_clusters: Mapped[list["VxlanRangeCluster"]] = relationship(
        back_populates="vxlan_range",
    )
    allocations: Mapped[list["VxlanAllocation"]] = relationship(
        back_populates="vxlan_range",
    )

    __table_args__ = (UniqueConstraint("name"),)


# Forward references for circular imports
from labomatics.core.db.models.vxlan_allocation import (  # noqa: E402
    VxlanAllocation,
)
from labomatics.core.db.models.vxlan_range_cluster import (  # noqa: E402
    VxlanRangeCluster,
)
