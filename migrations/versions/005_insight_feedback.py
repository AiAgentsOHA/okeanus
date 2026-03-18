"""Add insight_feedback table for user feedback loop and calibration.

Revision ID: 005_insight_feedback
Revises: 004_intelligence
Create Date: 2026-03-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005_insight_feedback"
down_revision = "004_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insight_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "insight_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("insights.id"),
            nullable=False,
        ),
        sa.Column("feedback_type", sa.String(20), nullable=False),
        sa.Column("user_score", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("outcome_observed", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_fb_insight", "insight_feedback", ["insight_id"])
    op.create_index("ix_fb_type", "insight_feedback", ["feedback_type"])
    op.create_index("ix_fb_created", "insight_feedback", ["created_at"])


def downgrade() -> None:
    op.drop_table("insight_feedback")
