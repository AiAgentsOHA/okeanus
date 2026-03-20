"""Geofence data models -- SQLAlchemy ORM + Pydantic schemas.

Geofence zones can be:
- Polygon: arbitrary boundary (EEZ, MPA, port limit)
- Circle: center point + radius in nautical miles

Rules can trigger on:
- ENTRY: vessel enters the zone
- EXIT: vessel leaves the zone
- LOITER: vessel stays in zone longer than threshold
- SPEED: vessel exceeds speed limit within zone
- AIS_OFF: vessel AIS gap detected within zone
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ZoneType(str, Enum):
    POLYGON = "polygon"
    CIRCLE = "circle"


class RuleType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    LOITER = "loiter"
    SPEED = "speed"
    AIS_OFF = "ais_off"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------

class GeofenceZone(Base):
    """A geographic zone with associated monitoring rules."""

    __tablename__ = "geofence_zones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    zone_type: Mapped[str] = mapped_column(
        String(20), nullable=False, doc="polygon or circle"
    )
    # For polygon zones: GeoJSON coordinates array
    # For circle zones: {"center": [lon, lat], "radius_nm": float}
    geometry_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, doc="Zone geometry definition"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Metadata
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
        doc="Zone category: mpa, eez, port, restricted, custom",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True, doc="Additional zone metadata"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class GeofenceRule(Base):
    """A monitoring rule attached to a geofence zone."""

    __tablename__ = "geofence_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    rule_type: Mapped[str] = mapped_column(
        String(20), nullable=False, doc="entry, exit, loiter, speed, ais_off"
    )
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="warning"
    )
    # Rule parameters stored as JSON
    # loiter: {"threshold_minutes": 60}
    # speed: {"max_speed_kn": 10}
    # ais_off: {"gap_hours": 6}
    parameters: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, doc="Rule-specific thresholds"
    )
    # Optional vessel filters
    # {"ship_types": [30, 31], "mmsi_list": [123456789], "flag_states": ["PA"]}
    vessel_filter: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, doc="Vessel filters for this rule"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class GeofenceAlert(Base):
    """An alert triggered when a vessel violates a geofence rule."""

    __tablename__ = "geofence_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    mmsi: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    # Event details
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, doc="Alert-specific details (speed, duration, etc.)"
    )
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ZoneCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str | None = None
    zone_type: ZoneType
    geometry_data: dict[str, Any] = Field(
        ...,
        description="For polygon: {\"coordinates\": [[[lon,lat],...]]}, "
        "for circle: {\"center\": [lon, lat], \"radius_nm\": float}",
    )
    category: str | None = None
    metadata: dict[str, Any] | None = None


class ZoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    zone_type: str
    geometry_data: dict[str, Any]
    is_active: bool
    category: str | None = None
    created_at: datetime
    updated_at: datetime


class ZoneUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    category: str | None = None


class RuleCreate(BaseModel):
    zone_id: uuid.UUID
    rule_type: RuleType
    severity: AlertSeverity = AlertSeverity.WARNING
    parameters: dict[str, Any] | None = None
    vessel_filter: dict[str, Any] | None = None


class RuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    zone_id: uuid.UUID
    rule_type: str
    severity: str
    parameters: dict[str, Any] | None = None
    vessel_filter: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    zone_id: uuid.UUID
    rule_id: uuid.UUID
    mmsi: int
    rule_type: str
    severity: str
    triggered_at: datetime
    lat: float
    lon: float
    details: dict[str, Any] | None = None
    is_acknowledged: bool
    acknowledged_at: datetime | None = None
    created_at: datetime
