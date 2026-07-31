from datetime import datetime
from uuid import UUID

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship


class IpAllocation(Base, UUIDPkMixin, TimestampMixin):
    """Allocation d'IP publique à un étudiant sur un cluster."""

    __tablename__ = "ip_allocation"

    ip_range_cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("ip_range_cluster.id", ondelete="RESTRICT"),
    )
    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    ip_address: Mapped[str] = mapped_column(
        INET,
    )
    allocated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
    )
    released_at: Mapped[datetime | None] = None

    # Relationships
    ip_range: Mapped["IpRange"] = relationship(
        back_populates="allocations",
    )
    student: Mapped["Student"] = relationship(  # type: ignore
        back_populates="ip_allocations",
    )

    __table_args__ = (
        Index(
            "idx_ip_alloc_address_active",
            "ip_range_cluster_id",
            "ip_address",
            postgresql_where=text("released_at IS NULL"),
            unique=True,
            comment="Une seule IP active par range/cluster",
        ),
        Index(
            "idx_ip_alloc_student_active",
            "ip_range_cluster_id",
            "student_id",
            postgresql_where=text("released_at IS NULL"),
            unique=True,
            comment="Une seule IP active par étudiant par cluster",
        ),
    )


# Forward references for circular imports
from backend.labomatics.core.db.models.ip_range import IpRange  # noqa: E402
from backend.labomatics.core.db.models.student import Student  # noqa: E402
