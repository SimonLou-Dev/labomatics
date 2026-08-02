from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import UUIDPkMixin


class Enrollment(Base, UUIDPkMixin):
    """Affectation étudiant → promo (historique immuable)."""

    __tablename__ = "enrollment"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
    )
    start_date: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )
    end_date: Mapped[datetime | None] = None
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.utcnow().replace(tzinfo=None),
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        back_populates="enrollments",
    )
    cohort: Mapped["Cohort"] = relationship(
        back_populates="enrollments",
    )

    __table_args__ = (
        Index(
            "uq_enrollment_active",
            "student_id",
            postgresql_where=text("end_date IS NULL"),
            unique=True,
        ),
        Index("idx_enrollment_student_date", "student_id", "start_date"),
    )


# Forward references for circular imports
from labomatics.core.db.models.cohort import Cohort  # noqa: E402
from labomatics.core.db.models.student import Student  # noqa: E402
