"""add vxlan_range.mtu

Revision ID: 2470168507ae
Revises: 2470168507ad
Create Date: 2026-08-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2470168507ae'
down_revision: Union[str, Sequence[str], None] = '2470168507ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('vxlan_range', sa.Column('mtu', sa.Integer(), nullable=False, server_default='1350'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('vxlan_range', 'mtu')
