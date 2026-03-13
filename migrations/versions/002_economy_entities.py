"""Add 7 economy entity tables.

Revision ID: 002_economy
Revises: 001_initial
Create Date: 2026-03-13

Adds standalone tables for structured blue economy data:
entities, time_series, flows, events, assessments, claims, relationships.
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision = "002_economy"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. entities (no FKs to other new tables)
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("identifier", sa.String(255), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.UniqueConstraint("source_name", "source_id", name="uq_entities_source"),
    )
    op.create_index("ix_entities_type_name", "entities", ["entity_type", "name"])
    op.create_index("ix_entities_identifier", "entities", ["identifier"])
    op.create_index("ix_entities_source_sid", "entities", ["source_name", "source_id"])
    op.create_index("ix_entities_geometry", "entities", ["geometry"], postgresql_using="gist")

    # 2. time_series (no FKs)
    op.create_table(
        "time_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("commodity", sa.String(100), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.UniqueConstraint("source_name", "source_id", name="uq_time_series_source"),
    )
    op.create_index("ix_time_series_code_ts", "time_series", ["code", "timestamp"])
    op.create_index("ix_time_series_source_ts", "time_series", ["source_name", "timestamp"])
    op.create_index("ix_time_series_commodity_country", "time_series", ["commodity", "country"])
    op.create_index("ix_time_series_geometry", "time_series", ["geometry"], postgresql_using="gist")

    # 3. flows (FKs → entities)
    op.create_table(
        "flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("flow_type", sa.String(50), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("dest_entity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount", sa.Float, nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("commodity", sa.String(100), nullable=True),
        sa.Column("purpose", sa.String(500), nullable=True),
    )
    op.create_index("ix_flows_type_ts", "flows", ["flow_type", "timestamp"])
    op.create_index("ix_flows_geometry", "flows", ["geometry"], postgresql_using="gist")

    # 4. events (no FKs)
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("economic_impact", sa.Float, nullable=True),
    )
    op.create_index("ix_events_type_ts", "events", ["event_type", "timestamp"])
    op.create_index("ix_events_geometry", "events", ["geometry"], postgresql_using="gist")

    # 5. assessments (FK → entities)
    op.create_table(
        "assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("assessor", sa.String(100), nullable=False),
        sa.Column("metric_code", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score_numeric", sa.Float, nullable=True),
        sa.Column("score_category", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("trend", sa.String(20), nullable=True),
    )
    op.create_index("ix_assessments_metric_ts", "assessments", ["metric_code", "timestamp"])
    op.create_index("ix_assessments_assessor_entity", "assessments", ["assessor", "entity_id"])

    # 6. claims (FK → entities)
    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("claimant_entity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("target_value", sa.Float, nullable=True),
        sa.Column("target_unit", sa.String(50), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("progress_percent", sa.Float, nullable=True),
    )
    op.create_index("ix_claims_status", "claims", ["status"])

    # 7. relationships (FKs → entities)
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("dest_entity_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("entities.id"), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("strength", sa.Float, nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
    )
    op.create_index("ix_relationships_type", "relationships", ["relationship_type"])
    op.create_index("ix_relationships_src_dest", "relationships",
                    ["source_entity_id", "dest_entity_id"])


def downgrade() -> None:
    op.drop_table("relationships")
    op.drop_table("claims")
    op.drop_table("assessments")
    op.drop_table("events")
    op.drop_table("flows")
    op.drop_table("time_series")
    op.drop_table("entities")
