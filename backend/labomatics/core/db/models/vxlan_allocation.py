from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class VxlanAllocation(Base, UUIDPkMixin, TimestampMixin):
    """Allocation de VNI à un étudiant sur un cluster."""

    __tablename__ = "vxlan_allocation"

    vxlan_range_cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("vxlan_range_cluster.id", ondelete="RESTRICT"),
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    vni: Mapped[int]
    subnet: Mapped[str] = mapped_column(
        CIDR,
    )
    allocated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
    )
    released_at: Mapped[datetime | None] = None

    # Relationships
    vxlan_range: Mapped["VxlanRange"] = relationship(
        back_populates="allocations",
    )
    student: Mapped["Student"] = relationship(  # type: ignore
        back_populates="vxlan_allocations",
    )

    __table_args__ = (
        Index(
            "idx_vxlan_alloc_vni_active",
            "vxlan_range_cluster_id",
            "vni",
            postgresql_where=text("released_at IS NULL"),
            unique=True,
        ),
        Index(
            "idx_vxlan_alloc_student_active",
            "vxlan_range_cluster_id",
            "student_id",
            postgresql_where=text("released_at IS NULL"),
            unique=True,
        ),
    )


# Forward references for circular imports
from labomatics.core.db.models.student import Student  # noqa: E402
from labomatics.core.db.models.vxlan_range import VxlanRange  # noqa: E402
