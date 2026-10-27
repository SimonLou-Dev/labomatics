"""add_teacher_table

Revision ID: 2a3b9274a8db
Revises: d01656277075
Create Date: 2026-10-27 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a3b9274a8db"
down_revision: str | Sequence[str] | None = "d01656277075"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teacher",
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("login", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("keycloak_user_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("login"),
        sa.UniqueConstraint("keycloak_user_id"),
    )

    # teacher_cohort.teacher_keycloak_id (UUID brut, sans FK) -> teacher_id (FK).
    # Aucun code applicatif ne peuplait cette table jusqu'ici (pas de UI de
    # gestion des profs) : vérifié vide en dev avant d'écrire cette migration.
    # Le backfill ci-dessous est donc un no-op documenté, pas une hypothèse.
    op.add_column("teacher_cohort", sa.Column("teacher_id", sa.Uuid(), nullable=True))
    op.drop_constraint(
        "teacher_cohort_teacher_keycloak_id_cohort_id_key",
        "teacher_cohort",
        type_="unique",
    )
    op.drop_column("teacher_cohort", "teacher_keycloak_id")
    op.alter_column("teacher_cohort", "teacher_id", nullable=False)
    op.create_foreign_key(
        "teacher_cohort_teacher_id_fkey",
        "teacher_cohort",
        "teacher",
        ["teacher_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "teacher_cohort_teacher_id_cohort_id_key",
        "teacher_cohort",
        ["teacher_id", "cohort_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "teacher_cohort_teacher_id_cohort_id_key", "teacher_cohort", type_="unique"
    )
    op.drop_constraint(
        "teacher_cohort_teacher_id_fkey", "teacher_cohort", type_="foreignkey"
    )
    op.drop_column("teacher_cohort", "teacher_id")
    op.add_column(
        "teacher_cohort", sa.Column("teacher_keycloak_id", sa.Uuid(), nullable=False)
    )
    op.create_unique_constraint(
        "teacher_cohort_teacher_keycloak_id_cohort_id_key",
        "teacher_cohort",
        ["teacher_keycloak_id", "cohort_id"],
    )
    op.drop_table("teacher")
