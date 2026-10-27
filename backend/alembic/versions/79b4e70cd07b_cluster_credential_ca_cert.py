"""cluster_credential_ca_cert

Revision ID: 79b4e70cd07b
Revises: c676a8ba0667
Create Date: 2026-10-17 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79b4e70cd07b"
down_revision: str | Sequence[str] | None = "c676a8ba0667"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cluster_credential",
        sa.Column("ca_cert", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cluster_credential", "ca_cert")
