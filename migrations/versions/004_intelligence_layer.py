"""Add intelligence layer tables: embeddings, knowledge_edges, insights, reasoning_traces.

Revision ID: 004_intelligence
Revises: 003_geofence
Create Date: 2026-03-18

Adds vector search and knowledge graph infrastructure:
embeddings (pgvector), knowledge_edges, insights, reasoning_traces.
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "004_intelligence"
down_revision = "003_geofence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. embeddings
    op.create_table(
        "embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_table", sa.String(50), nullable=False),
        sa.Column("text_content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column(
            "model_name",
            sa.String(100),
            server_default="BAAI/bge-small-en-v1.5",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("source_id", "source_type", name="uq_emb_source"),
    )
    op.create_index("ix_emb_source", "embeddings", ["source_id", "source_type"])
    op.execute(
        "CREATE INDEX ix_emb_cosine ON embeddings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # 2. knowledge_edges
    op.create_table(
        "knowledge_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_label", sa.String(255), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_label", sa.String(255), nullable=True),
        sa.Column("edge_type", sa.String(30), nullable=False),
        sa.Column("strength", sa.Float, server_default="1.0"),
        sa.Column("evidence_type", sa.String(50), nullable=True),
        sa.Column("evidence_detail", sa.Text, nullable=True),
        sa.Column("domain", sa.String(100), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ke_source", "knowledge_edges", ["source_id", "source_type"])
    op.create_index("ix_ke_target", "knowledge_edges", ["target_id", "target_type"])
    op.create_index("ix_ke_edge_type", "knowledge_edges", ["edge_type"])
    op.create_index("ix_ke_domain", "knowledge_edges", ["domain"])

    # 3. insights
    op.create_table(
        "insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("classification", sa.String(20), nullable=True),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
        sa.Column(
            "involved_domains",
            postgresql.ARRAY(sa.String),
            nullable=True,
        ),
        sa.Column("spatial_context", postgresql.JSONB, nullable=True),
        sa.Column("temporal_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("temporal_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generator", sa.String(100), nullable=True),
        sa.Column("critic_score", sa.Float, nullable=True),
        sa.Column("critic_notes", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="candidate",
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
    )
    op.create_index("ix_ins_type", "insights", ["insight_type"])
    op.create_index("ix_ins_status", "insights", ["status"])
    op.create_index("ix_ins_confidence", "insights", ["confidence"])

    # 4. reasoning_traces
    op.create_table(
        "reasoning_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "insight_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("insights.id"),
            nullable=True,
        ),
        sa.Column("phase", sa.String(20), nullable=False),
        sa.Column("input_text", sa.Text, nullable=False),
        sa.Column("output_text", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_rt_insight", "reasoning_traces", ["insight_id"])


def downgrade() -> None:
    op.drop_table("reasoning_traces")
    op.drop_table("insights")
    op.drop_table("knowledge_edges")
    op.drop_table("embeddings")
    op.execute("DROP EXTENSION IF EXISTS vector")
