"""Widen embedding column from vector(384) to vector(768) for nomic-embed-text-v1.5.

Revision ID: 006_embedding_768
Revises: 005_insight_feedback
Create Date: 2026-03-19
"""

from alembic import op

revision = "006_embedding_768"
down_revision = "005_insight_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Table is empty so this is safe and instant
    op.execute("DROP INDEX IF EXISTS ix_emb_cosine")
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(768)")
    op.execute(
        "CREATE INDEX ix_emb_cosine ON embeddings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_emb_cosine")
    op.execute("ALTER TABLE embeddings ALTER COLUMN embedding TYPE vector(384)")
    op.execute(
        "CREATE INDEX ix_emb_cosine ON embeddings "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
