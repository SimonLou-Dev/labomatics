"""drop_enrollment_dates

Revision ID: ed9a49a1c0f6
Revises: 2a3b9274a8db
Create Date: 2026-10-27 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed9a49a1c0f6"
down_revision: str | Sequence[str] | None = "2a3b9274a8db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # La durée d'un enrollment est désormais portée par la Cohort elle-même
    # (modifiable via l'UI admin, #53), pas par l'enrollment. Backfill toute
    # cohort encore sans dates (ex: créée avant #53) sur l'année scolaire
    # déduite de son `year`, pour ne pas casser la résolution "enrollment
    # actif" des étudiants déjà enregistrés.
    op.execute(
        """
        UPDATE cohort
        SET start_date = COALESCE(start_date, make_date(year, 9, 1)::timestamp),
            end_date = COALESCE(end_date, make_date(year + 1, 8, 31)::timestamp)
        WHERE start_date IS NULL OR end_date IS NULL
        """
    )

    op.drop_index(
        "uq_enrollment_active",
        table_name="enrollment",
        postgresql_where=sa.text("end_date IS NULL"),
    )
    op.drop_index("idx_enrollment_student_date", table_name="enrollment")
    op.drop_column("enrollment", "start_date")
    op.drop_column("enrollment", "end_date")


def downgrade() -> None:
    op.add_column("enrollment", sa.Column("start_date", sa.DateTime(), nullable=True))
    op.add_column("enrollment", sa.Column("end_date", sa.DateTime(), nullable=True))
    op.create_index(
        "idx_enrollment_student_date",
        "enrollment",
        ["student_id", "start_date"],
        unique=False,
    )
    op.create_index(
        "uq_enrollment_active",
        "enrollment",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("end_date IS NULL"),
    )
