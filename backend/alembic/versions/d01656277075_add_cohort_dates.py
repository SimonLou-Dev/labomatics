"""add_cohort_dates

Revision ID: d01656277075
Revises: 79b4e70cd07b
Create Date: 2026-10-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d01656277075"
down_revision: str | Sequence[str] | None = "79b4e70cd07b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cohort", sa.Column("start_date", sa.DateTime(), nullable=True))
    op.add_column("cohort", sa.Column("end_date", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("cohort", "end_date")
    op.drop_column("cohort", "start_date")
