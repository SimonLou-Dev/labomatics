from datetime import datetime
from uuid import UUID

from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class CohortCluster(Base, UUIDPkMixin, TimestampMixin):
    """Association promo ↔ cluster (many-to-many)."""

    __tablename__ = "cohort_cluster"

    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
    )
    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
    )
    added_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
    )

    # Relationships
    cohort: Mapped["Cohort"] = relationship(
        back_populates="clusters",
    )
    cluster: Mapped["Cluster"] = relationship(
        back_populates="cohort_clusters",
    )

    __table_args__ = (
        UniqueConstraint("cohort_id", "cluster_id"),
        Index("idx_cohort_cluster_cluster_id", "cluster_id"),
    )


# Forward references for circular imports
from backend.labomatics.core.db.models.cluster import Cluster  # noqa: E402
from backend.labomatics.core.db.models.cohort import Cohort  # noqa: E402
