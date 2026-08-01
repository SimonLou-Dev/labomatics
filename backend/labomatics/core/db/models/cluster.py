from typing import Optional

from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class Cluster(Base, UUIDPkMixin, TimestampMixin):
    """Cluster Proxmox."""

    __tablename__ = "cluster"

    name: Mapped[str] = mapped_column(
        unique=True,
    )
    url: Mapped[str] = mapped_column()
    default_storage: Mapped[str] = mapped_column()
    sdn_zone: Mapped[str] = mapped_column()
    wan_bridge: Mapped[str] = mapped_column(
        default="vmbr0",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
    )
    is_default_for_new_cohorts: Mapped[bool] = mapped_column(
        default=False,
    )

    # Relationships
    cohort_clusters: Mapped[list["CohortCluster"]] = relationship(
        back_populates="cluster",
    )
    credential: Mapped[Optional["ClusterCredential"]] = relationship(
        back_populates="cluster",
        uselist=False,
    )
    student_extras: Mapped[list["StudentClusterExtra"]] = relationship(
        back_populates="cluster",
    )
    vxlan_range_clusters: Mapped[list["VxlanRangeCluster"]] = relationship(
        back_populates="cluster",
    )
    ip_range_clusters: Mapped[list["IpRangeCluster"]] = relationship(
        back_populates="cluster",
    )
    lab_provisioning: Mapped[list["LabProvisioning"]] = relationship(
        back_populates="cluster",
    )

    __table_args__ = (
        Index(
            "idx_cluster_is_default",
            is_default_for_new_cohorts,
            postgresql_where=text("is_default_for_new_cohorts = true"),
        ),
    )


# Forward references for circular imports
from labomatics.core.db.models.cluster_credential import (  # noqa: E402
    ClusterCredential,
)
from labomatics.core.db.models.cohort_cluster import (  # noqa: E402
    CohortCluster,
)
from labomatics.core.db.models.ip_range_cluster import (  # noqa: E402
    IpRangeCluster,
)
from labomatics.core.db.models.lab_provisioning import (  # noqa: E402
    LabProvisioning,
)
from labomatics.core.db.models.student_cluster_extra import (  # noqa: E402
    StudentClusterExtra,
)
from labomatics.core.db.models.vxlan_range_cluster import (  # noqa: E402
    VxlanRangeCluster,
)
