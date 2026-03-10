"""Core observation model -- every observation in Okeanus inherits from this.

Provides both a SQLAlchemy ORM model (for PostGIS persistence) and a Pydantic
v2 model (for API serialization with GeoJSON output).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry, WKBElement
from geojson_pydantic import Feature, Point, Polygon
from pydantic import BaseModel, ConfigDict, Field, field_validator
from shapely import wkb
from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# SQLAlchemy declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class Observation(Base):
    """Universal observation record.

    Every row in the ocean data lake inherits these columns.  Source-specific
    detail lives either in typed subclass columns or in the ``payload`` JSONB
    column.

    The table uses single-table inheritance via ``obs_type`` so that all
    observations share a unified spatial/temporal index while each domain
    (physical, vessel, acoustic, biological, satellite) adds its own columns.

    .. note::
        Consider time-based partitioning on ``timestamp`` for production
        deployments with >100M rows.  Partition by month or quarter using
        PostgreSQL declarative partitioning.
    """

    __tablename__ = "observations"

    # -- Primary key --
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # -- Discriminator for single-table inheritance --
    obs_type: Mapped[str] = mapped_column(String(30), nullable=False)

    # -- Temporal --
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # -- Spatial (PostGIS) --
    # Point for point observations; Polygon stored via satellite subclass.
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
        nullable=False,
    )

    # -- Provenance --
    source_id: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, doc="Unique ID within the upstream source"
    )
    source_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, doc="Name of the upstream data source"
    )
    quality_score: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Quality/confidence score in [0.0, 1.0]"
    )

    # -- Linking keys --
    aphia_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, doc="WoRMS Aphia species identifier"
    )
    mrgid: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, doc="Marine Regions geography identifier"
    )
    mmsi: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, doc="Maritime Mobile Service Identity"
    )

    # -- Flexible payload --
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, doc="Source-specific data not captured by typed columns"
    )

    # -- Audit --
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __mapper_args__ = {
        "polymorphic_on": "obs_type",
        "polymorphic_identity": "observation",
    }

    __table_args__ = (
        # Spatial index (GIST) on geometry column
        Index("ix_observations_geometry", "geometry", postgresql_using="gist"),
        # Compound index for common query: source + time range
        Index("ix_observations_source_time", "source_name", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.id!s:.8} "
            f"type={self.obs_type} source={self.source_name} "
            f"t={self.timestamp}>"
        )


# ---------------------------------------------------------------------------
# Pydantic v2 model -- GeoJSON serialization
# ---------------------------------------------------------------------------

def _wkb_to_geojson(v: Any) -> dict[str, Any]:
    """Convert a WKBElement or raw bytes to a GeoJSON-compatible dict."""
    if isinstance(v, WKBElement):
        shapely_geom = wkb.loads(bytes(v.data))
    elif isinstance(v, (bytes, memoryview)):
        shapely_geom = wkb.loads(bytes(v))
    elif isinstance(v, dict):
        return v
    else:
        return v
    return shapely_geom.__geo_interface__


class ObservationBase(BaseModel):
    """Pydantic base for all observation API responses.

    Serialises the PostGIS geometry column as a GeoJSON Feature so that API
    consumers can directly render observations on a map.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    obs_type: str
    timestamp: datetime
    source_id: str
    source_name: str
    quality_score: float | None = None
    aphia_id: int | None = None
    mrgid: int | None = None
    mmsi: int | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    # Geometry is validated via field_validator and turned into GeoJSON dict
    geometry: dict[str, Any]

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any]:
        return _wkb_to_geojson(v)

    def to_feature(self) -> Feature:
        """Return this observation as a full GeoJSON Feature."""
        geom = self.geometry
        geom_type = geom.get("type", "Point")
        if geom_type == "Point":
            geometry = Point(**geom)
        else:
            geometry = Polygon(**geom)
        properties = self.model_dump(exclude={"geometry", "id"})
        return Feature(id=str(self.id), geometry=geometry, properties=properties)


class ObservationCreate(BaseModel):
    """Pydantic model for creating a new observation."""

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime
    geometry: dict[str, Any] = Field(
        ..., description="GeoJSON geometry object (Point or Polygon)"
    )
    source_id: str
    source_name: str
    quality_score: float | None = Field(None, ge=0.0, le=1.0)
    aphia_id: int | None = None
    mrgid: int | None = None
    mmsi: int | None = None
    payload: dict[str, Any] | None = None
