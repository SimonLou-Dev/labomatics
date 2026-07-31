from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import CIDR, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
        comment="Réseau base (ex. 10.100.0.0/12)",
    )
    exclusions: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Liste de CIDR à exclure",
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
from backend.labomatics.core.db.models.vxlan_allocation import (  # noqa: E402
    VxlanAllocation,
)
from backend.labomatics.core.db.models.vxlan_range_cluster import (  # noqa: E402
    VxlanRangeCluster,
)
