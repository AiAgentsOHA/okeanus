"""Vessel positions and tracks.

Sources: terrestrial AIS, satellite AIS (S-AIS), coastal radar.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Observation, ObservationBase, ObservationCreate

# ---------------------------------------------------------------------------
# SQLAlchemy ORM model
# ---------------------------------------------------------------------------

class VesselObservation(Observation):
    """A single AIS position report or radar track.

    Stores decoded AIS message fields alongside the base observation columns.
    The ``mmsi`` linking key lives on the parent ``Observation`` table.
    """

    __mapper_args__ = {"polymorphic_identity": "vessel"}

    imo: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True, doc="IMO ship number"
    )
    vessel_name: Mapped[str | None] = mapped_column(
        String(120), nullable=True, doc="Ship name from AIS static data"
    )
    call_sign: Mapped[str | None] = mapped_column(
        String(20), nullable=True, doc="Radio call sign"
    )
    ship_type: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="AIS ship type code (0-99)"
    )
    nav_status: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="AIS navigational status (0-15)"
    )
    sog: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Speed over ground in knots"
    )
    cog: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Course over ground in degrees"
    )
    heading: Mapped[int | None] = mapped_column(
        Integer, nullable=True, doc="True heading in degrees (0-359)"
    )
    destination: Mapped[str | None] = mapped_column(
        String(120), nullable=True, doc="Reported destination"
    )
    eta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="Estimated time of arrival"
    )
    draught: Mapped[float | None] = mapped_column(
        Float, nullable=True, doc="Current draught in metres"
    )


# ---------------------------------------------------------------------------
# Pydantic v2 models
# ---------------------------------------------------------------------------

class VesselObservationRead(ObservationBase):
    """API response model for a vessel observation."""

    model_config = ConfigDict(from_attributes=True)

    imo: int | None = None
    vessel_name: str | None = None
    call_sign: str | None = None
    ship_type: int | None = None
    nav_status: int | None = None
    sog: float | None = None
    cog: float | None = None
    heading: int | None = None
    destination: str | None = None
    eta: datetime | None = None
    draught: float | None = None


class VesselObservationCreate(ObservationCreate):
    """API request model for creating a vessel observation."""

    imo: int | None = None
    vessel_name: str | None = None
    call_sign: str | None = None
    ship_type: int | None = Field(None, ge=0, le=99)
    nav_status: int | None = Field(None, ge=0, le=15)
    sog: float | None = Field(None, ge=0.0)
    cog: float | None = Field(None, ge=0.0, lt=360.0)
    heading: int | None = Field(None, ge=0, le=359)
    destination: str | None = None
    eta: datetime | None = None
    draught: float | None = Field(None, ge=0.0)
