from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class LabProvisioning(Base, UUIDPkMixin, TimestampMixin):
    """État de provisioning du lab personnel par étudiant/administrateur/cluster."""

    __tablename__ = "lab_provisioning"

    owner_keycloak_id: Mapped[UUID] = mapped_column(PGUUID)
    owner_role: Mapped[str] = mapped_column()
    student_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
    )
    status: Mapped[str] = mapped_column()
    access_origin: Mapped[str] = mapped_column()
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
    student: Mapped["Student | None"] = relationship(  # type: ignore
        back_populates="lab_provisioning",
    )
    cluster: Mapped["Cluster"] = relationship(  # type: ignore
        back_populates="lab_provisioning",
    )
    ip_allocation: Mapped["IpAllocation | None"] = relationship(  # type: ignore
        foreign_keys=[ip_allocation_id],
    )
    vxlan_allocation: Mapped["VxlanAllocation | None"] = relationship(  # type: ignore
        foreign_keys=[vxlan_allocation_id],
    )
    vms: Mapped[list["LabVm"]] = relationship(  # type: ignore
        back_populates="lab_provisioning",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("student_id", "cluster_id"),
        UniqueConstraint(
            "owner_keycloak_id", "cluster_id", name="uq_lab_prov_owner_cluster"
        ),
        Index("idx_lab_prov_status", "status"),
        Index("idx_lab_prov_cluster", "cluster_id"),
    )


# Forward references for circular imports
from labomatics.core.db.models.cluster import Cluster  # noqa: E402
from labomatics.core.db.models.ip_allocation import IpAllocation  # noqa: E402
from labomatics.core.db.models.lab_vm import LabVm  # noqa: E402
from labomatics.core.db.models.student import Student  # noqa: E402
from labomatics.core.db.models.vxlan_allocation import VxlanAllocation  # noqa: E402
