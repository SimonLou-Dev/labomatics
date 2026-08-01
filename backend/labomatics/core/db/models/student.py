from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class Student(Base, UUIDPkMixin, TimestampMixin):
    """Étudiant."""

    __tablename__ = "student"

    external_id: Mapped[int] = mapped_column(
        unique=True,
    )
    last_name: Mapped[str]
    first_name: Mapped[str]
    email: Mapped[str] = mapped_column(
        unique=True,
    )
    login: Mapped[str] = mapped_column(
        unique=True,
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
    )
    left_at: Mapped[datetime | None] = None
    keycloak_user_id: Mapped[UUID | None] = mapped_column(
        unique=True,
        nullable=True,
    )
    proxmox_userid: Mapped[str | None] = mapped_column(
        unique=True,
        nullable=True,
    )

    # Relationships
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="student",
    )
    cluster_extras: Mapped[list["StudentClusterExtra"]] = relationship(
        back_populates="student",
    )
    vxlan_allocations: Mapped[list["VxlanAllocation"]] = relationship(
        back_populates="student",
    )
    ip_allocations: Mapped[list["IpAllocation"]] = relationship(
        back_populates="student",
    )
    lab_provisioning: Mapped[list["LabProvisioning"]] = relationship(
        back_populates="student",
    )


# Forward references for circular imports
from labomatics.core.db.models.enrollment import Enrollment  # noqa: E402
from labomatics.core.db.models.ip_allocation import (  # noqa: E402
    IpAllocation,
)
from labomatics.core.db.models.lab_provisioning import (  # noqa: E402
    LabProvisioning,
)
from labomatics.core.db.models.student_cluster_extra import (  # noqa: E402
    StudentClusterExtra,
)
from labomatics.core.db.models.vxlan_allocation import (  # noqa: E402
    VxlanAllocation,
)
