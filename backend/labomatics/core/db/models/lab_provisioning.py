from datetime import datetime
from uuid import UUID

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class LabProvisioning(Base, UUIDPkMixin, TimestampMixin):
    """État de provisioning du lab personnel par étudiant/cluster."""

    __tablename__ = "lab_provisioning"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
    )
    status: Mapped[str] = mapped_column(
        comment="pending|creating|active|deleting|deleted|error",
    )
    access_origin: Mapped[str] = mapped_column(
        comment="cohort|extra — figé au moment du provisioning",
    )
    vxlan_allocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("vxlan_allocation.id", ondelete="SET NULL"),
        nullable=True,
    )
    ip_allocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ip_allocation.id", ondelete="SET NULL"),
        nullable=True,
    )
    proxmox_pool: Mapped[str | None] = None
    proxmox_vm_id: Mapped[int | None] = None
    proxmox_vnet: Mapped[str | None] = None
    last_checked_at: Mapped[datetime | None] = None
    last_error: Mapped[str | None] = None

    # Relationships
    student: Mapped["Student"] = relationship(  # type: ignore
        back_populates="lab_provisioning",
    )
    cluster: Mapped["Cluster"] = relationship(  # type: ignore
        back_populates="lab_provisioning",
    )

    __table_args__ = (
        UniqueConstraint("student_id", "cluster_id"),
        Index("idx_lab_prov_status", "status"),
        Index("idx_lab_prov_cluster", "cluster_id"),
    )


# Forward references for circular imports
from backend.labomatics.core.db.models.cluster import Cluster  # noqa: E402
from backend.labomatics.core.db.models.student import Student  # noqa: E402
