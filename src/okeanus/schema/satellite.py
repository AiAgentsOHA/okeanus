"""Satellite scene metadata.

Sources: Sentinel-1 (SAR), Sentinel-2 (MSI), Sentinel-3 (OLCI/SLSTR),
MODIS, PACE, commercial SAR (ICEYE, Capella, Umbra).
"""

from __future__ import annotations

import enum

from pydantic import ConfigDict, Field
from sqlalchemy import Enum, Float, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Observation, ObservationBase, ObservationCreate


class OrbitDirection(enum.StrEnum):
    """Satellite orbit pass direction."""

    ASC = "ASC"
    DESC = "DESC"


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class SatelliteObservation(Observation):
    """Metadata for a satellite scene or product.

    The ``geometry`` column on the parent stores the scene bounding polygon.
    Band-level data and raster storage references go in the ``payload`` JSONB
    column or an external object store (referenced via ``scene_url``).

    .. note::
        The ``geometry`` on the parent model uses the generic GEOMETRY type
        and should store a Polygon for satellite scenes.
    """

    __mapper_args__ = {"polymorphic_identity": "satellite"}

    platform: Mapped[str | None] = mapped_column(
        String(60), nullable=True, index=True, doc="Satellite platform name"
    )
    sensor: Mapped[str | None] = mapped_column(
        String(60), nullable=True, doc="Sensor/instrument identifier"
    )
    product_type: Mapped[str | None] = mapped_column(
        String(60), nullable=True, doc="Product type (e.g. GRD, L2A, OC3)"
    )
    resolution_m: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Spatial resolution in metres"
    )
    cloud_cover_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Cloud cover percentage (0-100)"
    )
    orbit_direction: Mapped[OrbitDirection | None] = mapped_column(
        Enum(OrbitDirection, name="orbit_direction", create_constraint=True),
        nullable=True,
    )
    processing_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True, doc="Processing level (e.g. L0, L1, L2)"
    )
    bands: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, doc="List of spectral band identifiers"
    )
    scene_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, doc="URL to the scene data or STAC item"
    )


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------

class SatelliteObservationRead(ObservationBase):
    """API response model for a satellite scene."""

    model_config = ConfigDict(from_attributes=True)

    platform: str
    sensor: str
    product_type: str
    resolution_m: float
    cloud_cover_pct: float | None = None
    orbit_direction: OrbitDirection | None = None
    processing_level: str
    bands: list[str]
    scene_url: str


class SatelliteObservationCreate(ObservationCreate):
    """API request model for creating a satellite scene record."""

    platform: str
    sensor: str
    product_type: str
    resolution_m: float = Field(..., gt=0.0)
    cloud_cover_pct: float | None = Field(None, ge=0.0, le=100.0)
    orbit_direction: OrbitDirection | None = None
    processing_level: str
    bands: list[str]
    scene_url: str
