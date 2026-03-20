"""Add alerts table for anomaly detection and monitoring.

Revision ID: 007_alerts_table
Revises: 006_embedding_768
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007_alerts_table"
down_revision = "006_embedding_768"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(100), nullable=True),
    )
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_created", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_created")
    op.drop_index("ix_alerts_type")
    op.drop_index("ix_alerts_severity")
    op.drop_index("ix_alerts_status")
    op.drop_table("alerts")
