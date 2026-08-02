"""Modèle pour les VMs du lab personnel étudiant."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class LabVm(Base, UUIDPkMixin, TimestampMixin):
    """VM du lab personnel d'un étudiant."""

    __tablename__ = "lab_vm"

    lab_provisioning_id: Mapped[UUID] = mapped_column(
        ForeignKey("lab_provisioning.id", ondelete="CASCADE"),
    )
    name: Mapped[str]
    cluster_name: Mapped[str]
    state: Mapped[str]
    cores: Mapped[int]
    memory: Mapped[int]
    disk: Mapped[int]
    notes: Mapped[str | None] = None

    # Relationships
    lab_provisioning: Mapped[LabProvisioning] = relationship(  # type: ignore
        back_populates="vms",
    )

    __table_args__ = (
        Index("idx_lab_vm_provisioning", "lab_provisioning_id"),
        Index("idx_lab_vm_cluster", "cluster_name"),
        Index("idx_lab_vm_state", "state"),
    )


# Forward references for circular imports
from labomatics.core.db.models.lab_provisioning import (  # noqa: E402
    LabProvisioning,
)
