"""Physical ocean observations -- SST, salinity, currents, waves, sea level, wind.

Sources: CMEMS, HYCOM, NOAA buoys, Argo floats.
"""

from __future__ import annotations

import enum

from pydantic import ConfigDict
from sqlalchemy import Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Observation, ObservationBase, ObservationCreate


class PhysicalParameter(enum.StrEnum):
    """Measured physical parameter type."""

    SST = "SST"
    SALINITY = "SALINITY"
    CURRENT_U = "CURRENT_U"
    CURRENT_V = "CURRENT_V"
    WAVE_HEIGHT = "WAVE_HEIGHT"
    WAVE_PERIOD = "WAVE_PERIOD"
    SEA_LEVEL = "SEA_LEVEL"
    WIND_SPEED = "WIND_SPEED"
    WIND_DIR = "WIND_DIR"


# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class PhysicalObservation(Observation):
    """A single physical ocean measurement.

    Covers scalar oceanographic and meteorological variables at a point in
    space, time, and optionally depth.
    """

    __mapper_args__ = {"polymorphic_identity": "physical"}

    parameter: Mapped[PhysicalParameter] = mapped_column(
        Enum(PhysicalParameter, name="physical_parameter", create_constraint=True),
        nullable=True,
        index=True,
    )
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(
        String(30), nullable=True, doc="SI unit of the measurement"
    )
    depth_m: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Observation depth in metres (positive down)"
    )


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------

class PhysicalObservationRead(ObservationBase):
    """API response model for a physical observation."""

    model_config = ConfigDict(from_attributes=True)

    parameter: PhysicalParameter
    value: float
    unit: str
    depth_m: float | None = None


class PhysicalObservationCreate(ObservationCreate):
    """API request model for creating a physical observation."""

    parameter: PhysicalParameter
    value: float
    unit: str
    depth_m: float | None = None
