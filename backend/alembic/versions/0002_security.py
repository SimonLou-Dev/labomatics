"""Security: cluster_credential (chiffré), audit_log (v0.4).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

Tables créées:
- cluster_credential (token API Proxmox chiffré au repos, Fernet)
- audit_log (piste d'audit des actions sensibles)
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cluster_credential",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_id", sa.String(255), nullable=False),
        sa.Column("encrypted_token_secret", postgresql.BYTEA(), nullable=False),
        sa.Column(
            "encryption_key_version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "quota_config", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cluster_id"], ["cluster.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_id"),
    )

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_keycloak_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_role", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_audit_log_actor", "audit_log", ["actor_keycloak_id", "created_at"]
    )
    op.create_index(
        "idx_audit_log_resource", "audit_log", ["resource_type", "resource_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_audit_log_resource", table_name="audit_log")
    op.drop_index("idx_audit_log_actor", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("cluster_credential")
