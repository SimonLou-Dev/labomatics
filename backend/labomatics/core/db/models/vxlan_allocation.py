from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class VxlanAllocation(Base, UUIDPkMixin, TimestampMixin):
    """Allocation de VNI à un étudiant/administrateur sur un cluster."""

    __tablename__ = "vxlan_allocation"

    vxlan_range_cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("vxlan_range_cluster.id", ondelete="RESTRICT"),
    )
    owner_keycloak_id: Mapped[UUID] = mapped_column(PGUUID)
    owner_role: Mapped[str] = mapped_column()
    student_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
        nullable=True,
    )
    vni: Mapped[int]
    subnet: Mapped[str] = mapped_column(
        CIDR,
    )
    allocated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )
    released_at: Mapped[datetime | None] = None

    # Relationships
    student: Mapped["Student | None"] = relationship(  # type: ignore
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
            "idx_vxlan_alloc_owner_active",
            "owner_keycloak_id",
            "vni",
            postgresql_where=text("released_at IS NULL"),
            unique=True,
        ),
    )


# Forward references for circular imports
from labomatics.core.db.models.student import Student  # noqa: E402
