"""Add geofence zones, rules, and alerts tables.

Revision ID: 003_geofence
Revises: 002_economy
Create Date: 2026-03-13

Adds monitoring tables for geographic zone enforcement:
geofence_zones, geofence_rules, geofence_alerts.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_geofence"
down_revision = "002_economy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. geofence_zones
    op.create_table(
        "geofence_zones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("zone_type", sa.String(20), nullable=False),
        sa.Column("geometry_data", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
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
    op.create_index("ix_geofence_zones_name", "geofence_zones", ["name"])
    op.create_index("ix_geofence_zones_category", "geofence_zones", ["category"])

    # 2. geofence_rules
    op.create_table(
        "geofence_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("vessel_filter", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_geofence_rules_zone_id", "geofence_rules", ["zone_id"])

    # 3. geofence_alerts
    op.create_table(
        "geofence_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("zone_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mmsi", sa.Integer, nullable=False),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lat", sa.Float, nullable=False),
        sa.Column("lon", sa.Float, nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.Column("is_acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_geofence_alerts_zone_id", "geofence_alerts", ["zone_id"])
    op.create_index("ix_geofence_alerts_rule_id", "geofence_alerts", ["rule_id"])
    op.create_index("ix_geofence_alerts_mmsi", "geofence_alerts", ["mmsi"])
    op.create_index(
        "ix_geofence_alerts_triggered_at", "geofence_alerts", ["triggered_at"]
    )


def downgrade() -> None:
    op.drop_table("geofence_alerts")
    op.drop_table("geofence_rules")
    op.drop_table("geofence_zones")
