from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class StudentClusterExtra(Base, UUIDPkMixin, TimestampMixin):
    """Accès additionnel (non hérité de promo) d'étudiant à un cluster."""

    __tablename__ = "student_cluster_extra"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    cluster_id: Mapped[UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="RESTRICT"),
    )
    granted_by: Mapped[UUID | None] = None
    granted_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )
    revoked_at: Mapped[datetime | None] = None

    # Relationships
    student: Mapped["Student"] = relationship(  # type: ignore
        back_populates="cluster_extras",
    )
    cluster: Mapped["Cluster"] = relationship()  # type: ignore

    __table_args__ = (
        Index(
            "idx_student_cluster_extra_active",
            "student_id",
            "cluster_id",
            postgresql_where=text("revoked_at IS NULL"),
            unique=True,
        ),
    )


# Forward references for circular imports
from labomatics.core.db.models.cluster import Cluster  # noqa: E402
from labomatics.core.db.models.student import Student  # noqa: E402
