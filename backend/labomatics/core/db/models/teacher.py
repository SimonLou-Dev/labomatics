from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import TimestampMixin, UUIDPkMixin


class Teacher(Base, UUIDPkMixin, TimestampMixin):
    """Professeur, ajouté via l'UI admin (#58)."""

    __tablename__ = "teacher"

    last_name: Mapped[str]
    first_name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    login: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    keycloak_user_id: Mapped[UUID | None] = mapped_column(unique=True, nullable=True)

    # Relationships
    teacher_cohorts: Mapped[list["TeacherCohort"]] = relationship(
        back_populates="teacher",
    )


# Forward references for circular imports
from labomatics.core.db.models.teacher_cohort import TeacherCohort  # noqa: E402
