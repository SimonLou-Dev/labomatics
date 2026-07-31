from backend.labomatics.core.db.base import Base
from backend.labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Cohort(Base, UUIDPkMixin, TimestampMixin):
    """Promo (cohorte d'étudiants)."""

    __tablename__ = "cohort"

    name: Mapped[str]
    year: Mapped[int] = mapped_column(
        comment="Année de la promo",
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
    )

    # Relationships
    clusters: Mapped[list["CohortCluster"]] = relationship(
        back_populates="cohort",
    )
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="cohort",
    )
    teacher_cohorts: Mapped[list["TeacherCohort"]] = relationship(
        back_populates="cohort",
    )

    __table_args__ = (UniqueConstraint("name", "year"),)


# Forward references for circular imports
from backend.labomatics.core.db.models.cohort_cluster import (  # noqa: E402
    CohortCluster,
)
from backend.labomatics.core.db.models.enrollment import Enrollment  # noqa: E402
from backend.labomatics.core.db.models.teacher_cohort import (  # noqa: E402
    TeacherCohort,
)
