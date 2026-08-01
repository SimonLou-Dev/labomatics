from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class TeacherCohort(Base, UUIDPkMixin, TimestampMixin):
    """Association enseignant (Keycloak) ↔ promo."""

    __tablename__ = "teacher_cohort"

    teacher_keycloak_id: Mapped[UUID] = mapped_column()
    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
    )

    # Relationships
    cohort: Mapped["Cohort"] = relationship(
        back_populates="teacher_cohorts",
    )

    __table_args__ = (UniqueConstraint("teacher_keycloak_id", "cohort_id"),)


# Forward references for circular imports
from labomatics.core.db.models.cohort import Cohort  # noqa: E402
