from uuid import UUID

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class VxlanRangeCluster(Base, UUIDPkMixin, TimestampMixin):
    """Association VxlanRange ↔ Cluster (many-to-many)."""

    __tablename__ = "vxlan_range_cluster"

    vxlan_range_id: Mapped[UUID] = mapped_column(
        ForeignKey("vxlan_range.id", ondelete="RESTRICT"),
    )
    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
    )

    # Relationships
    vxlan_range: Mapped["VxlanRange"] = relationship(
        back_populates="range_clusters",
    )
    cluster: Mapped["Cluster"] = relationship()  # type: ignore

    __table_args__ = (UniqueConstraint("vxlan_range_id", "cluster_id"),)


# Forward references for circular imports
from backend.labomatics.core.db.models.cluster import Cluster  # noqa: E402
from backend.labomatics.core.db.models.vxlan_range import VxlanRange  # noqa: E402
