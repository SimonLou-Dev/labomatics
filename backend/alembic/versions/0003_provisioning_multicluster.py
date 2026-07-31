"""Provisioning multi-cluster (v0.5).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31

Tables créées:
- student_cluster_extra (accès additif étudiant → cluster)
- vxlan_range, vxlan_range_cluster, vxlan_allocation
- ip_range, ip_range_cluster, ip_allocation
- lab_provisioning (état par étudiant/cluster)
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_cluster_extra",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_student_cluster_extra_active",
        "student_cluster_extra",
        ["student_id", "cluster_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "vxlan_range",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(32), nullable=False, server_default="default"),
        sa.Column("vni_min", sa.Integer(), nullable=False),
        sa.Column("vni_max", sa.Integer(), nullable=False),
        sa.Column("base_network", postgresql.CIDR(), nullable=False),
        sa.Column("exclusions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
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

    op.create_table(
        "vxlan_range_cluster",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("vxlan_range_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["vxlan_range_id"], ["vxlan_range.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vxlan_range_id", "cluster_id"),
    )

    op.create_table(
        "vxlan_allocation",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vxlan_range_cluster_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vni", sa.Integer(), nullable=False),
        sa.Column("subnet", postgresql.CIDR(), nullable=False),
        sa.Column(
            "allocated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["vxlan_range_cluster_id"], ["vxlan_range_cluster.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_vxlan_alloc_student_active",
        "vxlan_allocation",
        ["vxlan_range_cluster_id", "student_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.create_index(
        "idx_vxlan_alloc_vni_active",
        "vxlan_allocation",
        ["vxlan_range_cluster_id", "vni"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )

    op.create_table(
        "ip_range",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(32), nullable=False, server_default="default"),
        sa.Column("network", postgresql.CIDR(), nullable=False),
        sa.Column("gateway", postgresql.INET(), nullable=False),
        sa.Column("exclusions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
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

    op.create_table(
        "ip_range_cluster",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ip_range_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.ForeignKeyConstraint(["ip_range_id"], ["ip_range.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_range_id", "cluster_id"),
    )

    op.create_table(
        "ip_allocation",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("ip_range_cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=False),
        sa.Column(
            "allocated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["ip_range_cluster_id"], ["ip_range_cluster.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_ip_alloc_address_active",
        "ip_allocation",
        ["ip_range_cluster_id", "ip_address"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.create_index(
        "idx_ip_alloc_student_active",
        "ip_allocation",
        ["ip_range_cluster_id", "student_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )

    op.create_table(
        "lab_provisioning",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("access_origin", sa.String(32), nullable=False),
        sa.Column("vxlan_allocation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_allocation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proxmox_pool", sa.String(64), nullable=True),
        sa.Column("proxmox_vm_id", sa.Integer(), nullable=True),
        sa.Column("proxmox_vnet", sa.String(8), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(512), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["ip_allocation_id"], ["ip_allocation.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["student_id"], ["student.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["vxlan_allocation_id"], ["vxlan_allocation.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "cluster_id"),
    )

    op.create_index("idx_lab_prov_cluster", "lab_provisioning", ["cluster_id"])
    op.create_index("idx_lab_prov_status", "lab_provisioning", ["status"])


def downgrade() -> None:
    op.drop_index("idx_lab_prov_status", table_name="lab_provisioning")
    op.drop_index("idx_lab_prov_cluster", table_name="lab_provisioning")
    op.drop_table("lab_provisioning")
    op.drop_index("idx_ip_alloc_student_active", table_name="ip_allocation")
    op.drop_index("idx_ip_alloc_address_active", table_name="ip_allocation")
    op.drop_table("ip_allocation")
    op.drop_table("ip_range_cluster")
    op.drop_table("ip_range")
    op.drop_index("idx_vxlan_alloc_vni_active", table_name="vxlan_allocation")
    op.drop_index("idx_vxlan_alloc_student_active", table_name="vxlan_allocation")
    op.drop_table("vxlan_allocation")
    op.drop_table("vxlan_range_cluster")
    op.drop_table("vxlan_range")
    op.drop_index(
        "idx_student_cluster_extra_active", table_name="student_cluster_extra"
    )
    op.drop_table("student_cluster_extra")
