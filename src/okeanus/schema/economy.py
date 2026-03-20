"""Blue economy entity models -- 7 standalone tables for structured economic data.

These are NOT part of the Observation STI hierarchy.  They provide normalised,
queryable tables for time series, entities, flows, events, assessments, claims,
and relationships produced by the 30 blue economy adapters.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry, WKBElement
from pydantic import BaseModel, ConfigDict, field_validator
from shapely import wkb
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Base


# ---------------------------------------------------------------------------
# Helper -- reuse the same WKB→GeoJSON converter as base.py
# ---------------------------------------------------------------------------

def _wkb_to_geojson(v: Any) -> dict[str, Any] | None:
    if v is None:
        return None
    if isinstance(v, WKBElement):
        shapely_geom = wkb.loads(bytes(v.data))
    elif isinstance(v, (bytes, memoryview)):
        shapely_geom = wkb.loads(bytes(v))
    elif isinstance(v, dict):
        return v
    else:
        return v
    return shapely_geom.__geo_interface__


# ===================================================================
# ORM Models
# ===================================================================


class TimeSeries(Base):
    """Time-indexed economic data point -- prices, indices, indicators."""

    __tablename__ = "time_series"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commodity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("source_name", "source_id", name="uq_time_series_source"),
        Index("ix_time_series_code_ts", "code", "timestamp"),
        Index("ix_time_series_source_ts", "source_name", "timestamp"),
        Index("ix_time_series_commodity_country", "commodity", "country"),
        Index("ix_time_series_geometry", "geometry", postgresql_using="gist"),
        Index("ix_timeseries_entity", "entity_id"),
    )


class Entity(Base):
    """Named thing -- organisation, port, MPA, fishery, country, project."""

    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identifier: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        UniqueConstraint("source_name", "source_id", name="uq_entities_source"),
        Index("ix_entities_type_name", "entity_type", "name"),
        Index("ix_entities_identifier", "identifier"),
        Index("ix_entities_source_sid", "source_name", "source_id"),
        Index("ix_entities_geometry", "geometry", postgresql_using="gist"),
    )


class Flow(Base):
    """Directional movement of money or goods between entities."""

    __tablename__ = "flows"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    flow_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    dest_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commodity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_flows_type_ts", "flow_type", "timestamp"),
        Index("ix_flows_geometry", "geometry", postgresql_using="gist"),
        Index("ix_flows_source_entity", "source_entity_id", postgresql_where=text("source_entity_id IS NOT NULL")),
        Index("ix_flows_dest_entity", "dest_entity_id", postgresql_where=text("dest_entity_id IS NOT NULL")),
    )


class Event(Base):
    """Discrete occurrence -- flood claim, MPA designation, spill."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    economic_impact: Mapped[float | None] = mapped_column(Float, nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_events_type_ts", "event_type", "timestamp"),
        Index("ix_events_geometry", "geometry", postgresql_using="gist"),
        Index("ix_events_entity", "entity_id"),
    )


class Assessment(Base):
    """Rating, score, or certification for an entity."""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    assessor: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    trend: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        Index("ix_assessments_metric_ts", "metric_code", "timestamp"),
        Index("ix_assessments_assessor_entity", "assessor", "entity_id"),
        Index("ix_assessments_entity", "entity_id"),
    )


class Claim(Base):
    """Pledge with delivery tracking -- Our Ocean commitments, etc."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    claimant_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    progress_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_claims_status", "status"),
    )


class Relationship(Base):
    """Typed link between two entities -- operates, invests_in, regulates."""

    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geometry: Mapped[Any | None] = mapped_column(
        Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=True
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Domain columns
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    dest_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_relationships_type", "relationship_type"),
        Index("ix_relationships_src_dest", "source_entity_id", "dest_entity_id"),
    )


# ===================================================================
# Pydantic Read Models
# ===================================================================


class TimeSeriesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    code: str
    name: str | None = None
    timestamp: datetime
    value: float
    unit: str | None = None
    commodity: str | None = None
    country: str | None = None
    entity_id: uuid.UUID | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)


class EntityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    entity_type: str
    name: str
    identifier: str | None = None
    country: str | None = None
    sector: str | None = None
    status: str | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)


class FlowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    flow_type: str
    source_entity_id: uuid.UUID | None = None
    dest_entity_id: uuid.UUID | None = None
    timestamp: datetime | None = None
    amount: float | None = None
    currency: str | None = None
    unit: str | None = None
    commodity: str | None = None
    purpose: str | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    event_type: str
    name: str | None = None
    description: str | None = None
    timestamp: datetime
    severity: str | None = None
    economic_impact: float | None = None
    entity_id: uuid.UUID | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    entity_id: uuid.UUID | None = None
    assessor: str
    metric_code: str
    timestamp: datetime | None = None
    score_numeric: float | None = None
    score_category: str | None = None
    confidence: float | None = None
    trend: str | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    claimant_entity_id: uuid.UUID | None = None
    name: str | None = None
    target_value: float | None = None
    target_unit: str | None = None
    deadline: datetime | None = None
    status: str | None = None
    progress_percent: float | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)


class Alert(Base):
    """System-generated alert from anomaly detection, change-point, or pattern match."""

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_type", "alert_type"),
        Index("ix_alerts_created", "created_at"),
    )


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_type: str
    severity: str
    source_type: str
    source_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    payload: dict[str, Any] | None = None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None
    resolved_by: str | None = None


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_name: str
    source_id: str
    quality_score: float | None = None
    geometry: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    source_entity_id: uuid.UUID
    dest_entity_id: uuid.UUID
    relationship_type: str
    strength: float | None = None
    status: str | None = None

    @field_validator("geometry", mode="before")
    @classmethod
    def parse_geometry(cls, v: Any) -> dict[str, Any] | None:
        return _wkb_to_geojson(v)
