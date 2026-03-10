"""Initial schema -- unified observations table with STI.

Revision ID: 001_initial
Revises:
Create Date: 2026-03-09

Creates the ``observations`` table using single-table inheritance to store
all ocean observation types (physical, vessel, acoustic, biological,
satellite) in a single spatially-indexed table.
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure PostGIS extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Create enum types
    physical_parameter_enum = postgresql.ENUM(
        "SST", "SALINITY", "CURRENT_U", "CURRENT_V",
        "WAVE_HEIGHT", "WAVE_PERIOD", "SEA_LEVEL",
        "WIND_SPEED", "WIND_DIR",
        name="physical_parameter",
        create_type=True,
    )
    observation_method_enum = postgresql.ENUM(
        "VISUAL", "EDNA", "ACOUSTIC", "CAMERA", "NET_TRAWL", "SATELLITE",
        name="observation_method",
        create_type=True,
    )
    orbit_direction_enum = postgresql.ENUM(
        "ASC", "DESC",
        name="orbit_direction",
        create_type=True,
    )

    # Enums are created automatically by create_table via create_type=True

    # ------------------------------------------------------------------
    # observations -- single-table inheritance for all observation types
    # ------------------------------------------------------------------
    # Consider time-based partitioning on `timestamp` for production
    # deployments with >100M rows.  Partition by month using:
    #   PARTITION BY RANGE (timestamp)
    # Then create child tables per month.
    # ------------------------------------------------------------------
    op.create_table(
        "observations",
        # -- Base columns --
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("obs_type", sa.String(30), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("source_name", sa.String(100), nullable=False),
        sa.Column("quality_score", sa.Float, nullable=True),
        sa.Column("aphia_id", sa.Integer, nullable=True),
        sa.Column("mrgid", sa.Integer, nullable=True),
        sa.Column("mmsi", sa.Integer, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),

        # -- Physical columns --
        sa.Column("parameter", physical_parameter_enum, nullable=True),
        sa.Column("value", sa.Float, nullable=True),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("depth_m", sa.Float, nullable=True),

        # -- Vessel columns --
        sa.Column("imo", sa.Integer, nullable=True),
        sa.Column("vessel_name", sa.String(120), nullable=True),
        sa.Column("call_sign", sa.String(20), nullable=True),
        sa.Column("ship_type", sa.Integer, nullable=True),
        sa.Column("nav_status", sa.Integer, nullable=True),
        sa.Column("sog", sa.Float, nullable=True),
        sa.Column("cog", sa.Float, nullable=True),
        sa.Column("heading", sa.Integer, nullable=True),
        sa.Column("destination", sa.String(120), nullable=True),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draught", sa.Float, nullable=True),

        # -- Acoustic columns --
        sa.Column("frequency_min_hz", sa.Float, nullable=True),
        sa.Column("frequency_max_hz", sa.Float, nullable=True),
        sa.Column("duration_s", sa.Float, nullable=True),
        sa.Column("spl_db", sa.Float, nullable=True),
        sa.Column("classification", sa.String(120), nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("classifier_model", sa.String(120), nullable=True),

        # -- Biological columns --
        sa.Column("taxon_aphia_id", sa.Integer, nullable=True),
        sa.Column("taxon_name", sa.String(255), nullable=True),
        sa.Column("taxon_rank", sa.String(50), nullable=True),
        sa.Column("abundance", sa.Float, nullable=True),
        sa.Column("biomass_kg", sa.Float, nullable=True),
        sa.Column("observation_method", observation_method_enum, nullable=True),
        sa.Column("life_stage", sa.String(50), nullable=True),

        # -- Satellite columns --
        sa.Column("platform", sa.String(60), nullable=True),
        sa.Column("sensor", sa.String(60), nullable=True),
        sa.Column("product_type", sa.String(60), nullable=True),
        sa.Column("resolution_m", sa.Float, nullable=True),
        sa.Column("cloud_cover_pct", sa.Float, nullable=True),
        sa.Column("orbit_direction", orbit_direction_enum, nullable=True),
        sa.Column("processing_level", sa.String(20), nullable=True),
        sa.Column("bands", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("scene_url", sa.String(500), nullable=True),
    )

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------
    # Spatial index (GIST) on geometry
    op.create_index(
        "ix_observations_geometry",
        "observations",
        ["geometry"],
        postgresql_using="gist",
    )

    # Temporal index
    op.create_index("ix_observations_timestamp", "observations", ["timestamp"])

    # Source indexes
    op.create_index("ix_observations_source_id", "observations", ["source_id"])
    op.create_index("ix_observations_source_name", "observations", ["source_name"])

    # Compound index for common query: source + time range
    op.create_index(
        "ix_observations_source_time",
        "observations",
        ["source_name", "timestamp"],
    )

    # Linking-key indexes
    op.create_index("ix_observations_aphia_id", "observations", ["aphia_id"])
    op.create_index("ix_observations_mrgid", "observations", ["mrgid"])
    op.create_index("ix_observations_mmsi", "observations", ["mmsi"])

    # Domain-specific indexes
    op.create_index("ix_observations_parameter", "observations", ["parameter"])
    op.create_index("ix_observations_imo", "observations", ["imo"])
    op.create_index("ix_observations_classification", "observations", ["classification"])
    op.create_index("ix_observations_taxon_name", "observations", ["taxon_name"])
    op.create_index("ix_observations_taxon_aphia_id", "observations", ["taxon_aphia_id"])
    op.create_index("ix_observations_observation_method", "observations", ["observation_method"])
    op.create_index("ix_observations_platform", "observations", ["platform"])

    # Discriminator index for type-specific queries
    op.create_index("ix_observations_obs_type", "observations", ["obs_type"])


def downgrade() -> None:
    op.drop_table("observations")
    op.execute("DROP TYPE IF EXISTS physical_parameter")
    op.execute("DROP TYPE IF EXISTS observation_method")
    op.execute("DROP TYPE IF EXISTS orbit_direction")
