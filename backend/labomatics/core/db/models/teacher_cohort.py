from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class TeacherCohort(Base, UUIDPkMixin, TimestampMixin):
    """Association professeur ↔ promo."""

    __tablename__ = "teacher_cohort"

    teacher_id: Mapped[UUID] = mapped_column(
        ForeignKey("teacher.id", ondelete="RESTRICT"),
    )
    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
    )

    # Relationships
    teacher: Mapped["Teacher"] = relationship(
        back_populates="teacher_cohorts",
    )
    cohort: Mapped["Cohort"] = relationship(
        back_populates="teacher_cohorts",
    )

    __table_args__ = (UniqueConstraint("teacher_id", "cohort_id"),)


# Forward references for circular imports
from labomatics.core.db.models.cohort import Cohort  # noqa: E402
from labomatics.core.db.models.teacher import Teacher  # noqa: E402
