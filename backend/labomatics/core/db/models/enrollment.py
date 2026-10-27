from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from labomatics.core.db.base import Base
from labomatics.core.db.mixin import UUIDPkMixin


class Enrollment(Base, UUIDPkMixin):
    """Affectation étudiant → promo (historique immuable).

    Ne porte plus ses propres dates (#53) : la durée est désormais portée par
    la `Cohort` elle-même (modifiable via l'UI admin), pour éviter d'avoir
    deux sources de vérité sur "quand" un étudiant est actif dans sa promo.
    """

    __tablename__ = "enrollment"

    student_id: Mapped[UUID] = mapped_column(
        ForeignKey("student.id", ondelete="RESTRICT"),
    )
    cohort_id: Mapped[UUID] = mapped_column(
        ForeignKey("cohort.id", ondelete="RESTRICT"),
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        back_populates="enrollments",
    )
    cohort: Mapped["Cohort"] = relationship(
        back_populates="enrollments",
    )

    def is_active(self, at: datetime | None = None) -> bool:
        """Vrai si `at` (par défaut: maintenant) tombe dans la fenêtre de la cohort.

        Nécessite que `cohort` soit chargée (selectinload) et que ses dates
        soient définies ; sinon considéré comme non actif (prudence par défaut
        plutôt que de supposer un étudiant actif sans date confirmée).
        """
        at = at or datetime.now()
        cohort = self.cohort
        if cohort is None or cohort.start_date is None or cohort.end_date is None:
            return False
        return cohort.start_date <= at <= cohort.end_date


# Forward references for circular imports
from labomatics.core.db.models.cohort import Cohort  # noqa: E402
from labomatics.core.db.models.student import Student  # noqa: E402
