"""Merge 007_alerts_table and 007_lineage_tables heads.

Revision ID: 008_merge_alerts_lineage
Revises: 007_alerts_table, 007_lineage_tables
Create Date: 2026-03-20
"""

revision = "008_merge_alerts_lineage"
down_revision = ("007_alerts_table", "007_lineage_tables")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
