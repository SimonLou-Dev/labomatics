from typing import Optional

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Cluster(Base, UUIDPkMixin, TimestampMixin):
    """Cluster Proxmox."""

    __tablename__ = "cluster"

    name: Mapped[str] = mapped_column(
        unique=True,
        comment="Nom unique du cluster (ex. labomatics-prod1)",
    )
    url: Mapped[str] = mapped_column(
        comment="URL API Proxmox",
    )
    default_storage: Mapped[str] = mapped_column(
        comment="Storage par défaut",
    )
    sdn_zone: Mapped[str] = mapped_column(
        comment="Zone SDN VXLAN",
    )
    wan_bridge: Mapped[str] = mapped_column(
        default="vmbr0",
        comment="Bridge WAN (défaut vmbr0)",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
    )
    is_default_for_new_cohorts: Mapped[bool] = mapped_column(
        default=False,
        comment="Cluster par défaut pour les nouvelles promos",
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
from backend.labomatics.core.db.models.cluster_credential import (  # noqa: E402
    ClusterCredential,
)
from backend.labomatics.core.db.models.cohort_cluster import (  # noqa: E402
    CohortCluster,
)
from backend.labomatics.core.db.models.ip_range_cluster import (  # noqa: E402
    IpRangeCluster,
)
from backend.labomatics.core.db.models.lab_provisioning import (  # noqa: E402
    LabProvisioning,
)
from backend.labomatics.core.db.models.student_cluster_extra import (  # noqa: E402
    StudentClusterExtra,
)
from backend.labomatics.core.db.models.vxlan_range_cluster import (  # noqa: E402
    VxlanRangeCluster,
)
