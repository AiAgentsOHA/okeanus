"""Add lineage_nodes and lineage_edges tables for data provenance tracking.

Revision ID: 007_lineage_tables
Revises: 006_embedding_768
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "007_lineage_tables"
down_revision = "006_embedding_768"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lineage_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("node_type", sa.String(30), nullable=False),
        sa.Column("name", sa.String(500), nullable=True),
        sa.Column("table_name", sa.String(100), nullable=True),
        sa.Column("record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_name", sa.String(200), nullable=True),
        sa.Column("transform_name", sa.String(200), nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lineage_nodes_type", "lineage_nodes", ["node_type"])
    op.create_index("ix_lineage_nodes_record", "lineage_nodes", ["table_name", "record_id"])
    op.create_index("ix_lineage_nodes_source", "lineage_nodes", ["source_name"])

    op.create_table(
        "lineage_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("lineage_nodes.id"), nullable=False),
        sa.Column("child_id", UUID(as_uuid=True), sa.ForeignKey("lineage_nodes.id"), nullable=False),
        sa.Column("edge_type", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_lineage_edges_parent", "lineage_edges", ["parent_id"])
    op.create_index("ix_lineage_edges_child", "lineage_edges", ["child_id"])
    op.create_index("ix_lineage_edges_type", "lineage_edges", ["edge_type"])


def downgrade() -> None:
    op.drop_table("lineage_edges")
    op.drop_table("lineage_nodes")
