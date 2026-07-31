"""Identity socle (v0.4).

Revision ID: 0001
Revises:
Create Date: 2026-07-31

Tables créées:
- cluster
- cohort
- cohort_cluster
- student
- enrollment
- teacher_cohort
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cluster",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("default_storage", sa.String(64), nullable=False),
        sa.Column("sdn_zone", sa.String(32), nullable=False),
        sa.Column("wan_bridge", sa.String(32), nullable=False, server_default="vmbr0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "is_default_for_new_cohorts",
            sa.Boolean(),
            nullable=False,
            server_default="false",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_index(
        "idx_cluster_is_default",
        "cluster",
        ["is_default_for_new_cohorts"],
        unique=False,
        postgresql_where=sa.text("is_default_for_new_cohorts = true"),
    )

    op.create_table(
        "cohort",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "year"),
    )

    op.create_table(
        "cohort_cluster",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
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
        sa.ForeignKeyConstraint(["cohort_id"], ["cohort.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_id", "cluster_id"),
    )

    op.create_index("idx_cohort_cluster_cluster_id", "cohort_cluster", ["cluster_id"])

    op.create_table(
        "student",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("external_id", sa.Integer(), nullable=False),
        sa.Column("last_name", sa.String(128), nullable=False),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("login", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("keycloak_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proxmox_userid", sa.String(128), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("external_id"),
        sa.UniqueConstraint("keycloak_user_id"),
        sa.UniqueConstraint("login"),
        sa.UniqueConstraint("proxmox_userid"),
    )

    op.create_table(
        "enrollment",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "start_date",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cohort_id"], ["cohort.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "uq_enrollment_active",
        "enrollment",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("end_date IS NULL"),
    )
    op.create_index(
        "idx_enrollment_student_date", "enrollment", ["student_id", "start_date"]
    )

    op.create_table(
        "teacher_cohort",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("teacher_keycloak_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["cohort_id"], ["cohort.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("teacher_keycloak_id", "cohort_id"),
    )


def downgrade() -> None:
    op.drop_table("teacher_cohort")
    op.drop_index("idx_enrollment_student_date", table_name="enrollment")
    op.drop_index("uq_enrollment_active", table_name="enrollment")
    op.drop_table("enrollment")
    op.drop_table("student")
    op.drop_index("idx_cohort_cluster_cluster_id", table_name="cohort_cluster")
    op.drop_table("cohort_cluster")
    op.drop_table("cohort")
    op.drop_index("idx_cluster_is_default", table_name="cluster")
    op.drop_table("cluster")
