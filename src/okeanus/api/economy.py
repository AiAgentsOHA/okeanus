"""Blue economy query endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from geoalchemy2.functions import ST_MakeEnvelope
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from okeanus.db.postgres import async_session_factory
from okeanus.schema.economy import (
    Assessment,
    AssessmentRead,
    Entity,
    EntityRead,
    Event,
    EventRead,
    Flow,
    FlowRead,
    Relationship,
    RelationshipRead,
    TimeSeries,
    TimeSeriesRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/economy", tags=["economy"])


@router.get("/timeseries")
async def list_timeseries(
    code: Annotated[str | None, Query(description="Series code")] = None,
    commodity: Annotated[str | None, Query(description="Commodity filter")] = None,
    country: Annotated[str | None, Query(description="Country ISO code")] = None,
    source_name: Annotated[str | None, Query(description="Data source name")] = None,
    entity_id: Annotated[uuid.UUID | None, Query(description="Linked entity UUID")] = None,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    bbox: Annotated[str | None, Query(description="Bounding box: west,south,east,north")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Query time series economic data."""
    stmt = select(TimeSeries)
    count_stmt = select(func.count()).select_from(TimeSeries)

    if code:
        stmt = stmt.where(TimeSeries.code == code)
        count_stmt = count_stmt.where(TimeSeries.code == code)
    if commodity:
        stmt = stmt.where(TimeSeries.commodity == commodity)
        count_stmt = count_stmt.where(TimeSeries.commodity == commodity)
    if country:
        stmt = stmt.where(TimeSeries.country == country)
        count_stmt = count_stmt.where(TimeSeries.country == country)
    if source_name:
        stmt = stmt.where(TimeSeries.source_name == source_name)
        count_stmt = count_stmt.where(TimeSeries.source_name == source_name)
    if entity_id:
        stmt = stmt.where(TimeSeries.entity_id == entity_id)
        count_stmt = count_stmt.where(TimeSeries.entity_id == entity_id)
    if time_start:
        stmt = stmt.where(TimeSeries.timestamp >= time_start)
        count_stmt = count_stmt.where(TimeSeries.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(TimeSeries.timestamp <= time_end)
        count_stmt = count_stmt.where(TimeSeries.timestamp <= time_end)
    if bbox:
        w, s, e, n = [float(x) for x in bbox.split(",")]
        envelope = ST_MakeEnvelope(w, s, e, n, 4326)
        stmt = stmt.where(TimeSeries.geometry.ST_Intersects(envelope))
        count_stmt = count_stmt.where(TimeSeries.geometry.ST_Intersects(envelope))

    stmt = stmt.order_by(TimeSeries.timestamp.desc()).offset(offset).limit(limit)

    async with async_session_factory() as session:
        total = (await session.execute(count_stmt)).scalar_one()
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [TimeSeriesRead.model_validate(r).model_dump() for r in rows],
        "total": total,
    }


@router.get("/entities")
async def list_entities(
    entity_type: Annotated[str | None, Query(description="Entity type filter")] = None,
    name: Annotated[str | None, Query(description="Name search (ilike)")] = None,
    country: Annotated[str | None, Query(description="Country ISO code")] = None,
    sector: Annotated[str | None, Query(description="Sector filter")] = None,
    bbox: Annotated[str | None, Query(description="Bounding box: west,south,east,north")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Query economic entities."""
    stmt = select(Entity)
    count_stmt = select(func.count()).select_from(Entity)

    if entity_type:
        stmt = stmt.where(Entity.entity_type == entity_type)
        count_stmt = count_stmt.where(Entity.entity_type == entity_type)
    if name:
        stmt = stmt.where(Entity.name.ilike(f"%{name}%"))
        count_stmt = count_stmt.where(Entity.name.ilike(f"%{name}%"))
    if country:
        stmt = stmt.where(Entity.country == country)
        count_stmt = count_stmt.where(Entity.country == country)
    if sector:
        stmt = stmt.where(Entity.sector == sector)
        count_stmt = count_stmt.where(Entity.sector == sector)
    if bbox:
        w, s, e, n = [float(x) for x in bbox.split(",")]
        envelope = ST_MakeEnvelope(w, s, e, n, 4326)
        stmt = stmt.where(Entity.geometry.ST_Intersects(envelope))
        count_stmt = count_stmt.where(Entity.geometry.ST_Intersects(envelope))

    stmt = stmt.offset(offset).limit(limit)

    async with async_session_factory() as session:
        total = (await session.execute(count_stmt)).scalar_one()
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [EntityRead.model_validate(r).model_dump() for r in rows],
        "total": total,
    }


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: uuid.UUID) -> dict[str, Any]:
    """Get a single entity with related assessments and relationships."""
    async with async_session_factory() as session:
        entity = (
            await session.execute(select(Entity).where(Entity.id == entity_id))
        ).scalar_one_or_none()
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")

        assessments = (
            await session.execute(
                select(Assessment).where(Assessment.entity_id == entity_id)
            )
        ).scalars().all()

        relationships = (
            await session.execute(
                select(Relationship).where(
                    (Relationship.source_entity_id == entity_id)
                    | (Relationship.dest_entity_id == entity_id)
                )
            )
        ).scalars().all()

    return {
        "entity": EntityRead.model_validate(entity).model_dump(),
        "assessments": [AssessmentRead.model_validate(a).model_dump() for a in assessments],
        "relationships": [RelationshipRead.model_validate(r).model_dump() for r in relationships],
    }


@router.get("/flows")
async def list_flows(
    flow_type: Annotated[str | None, Query(description="Flow type filter")] = None,
    commodity: Annotated[str | None, Query(description="Commodity filter")] = None,
    source_entity_id: Annotated[uuid.UUID | None, Query(description="Source entity UUID")] = None,
    dest_entity_id: Annotated[uuid.UUID | None, Query(description="Destination entity UUID")] = None,
    min_amount: Annotated[float | None, Query(description="Minimum flow amount")] = None,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Query economic flows."""
    stmt = select(Flow)
    count_stmt = select(func.count()).select_from(Flow)

    if flow_type:
        stmt = stmt.where(Flow.flow_type == flow_type)
        count_stmt = count_stmt.where(Flow.flow_type == flow_type)
    if commodity:
        stmt = stmt.where(Flow.commodity == commodity)
        count_stmt = count_stmt.where(Flow.commodity == commodity)
    if source_entity_id:
        stmt = stmt.where(Flow.source_entity_id == source_entity_id)
        count_stmt = count_stmt.where(Flow.source_entity_id == source_entity_id)
    if dest_entity_id:
        stmt = stmt.where(Flow.dest_entity_id == dest_entity_id)
        count_stmt = count_stmt.where(Flow.dest_entity_id == dest_entity_id)
    if min_amount is not None:
        stmt = stmt.where(Flow.amount >= min_amount)
        count_stmt = count_stmt.where(Flow.amount >= min_amount)
    if time_start:
        stmt = stmt.where(Flow.timestamp >= time_start)
        count_stmt = count_stmt.where(Flow.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(Flow.timestamp <= time_end)
        count_stmt = count_stmt.where(Flow.timestamp <= time_end)

    stmt = stmt.offset(offset).limit(limit)

    async with async_session_factory() as session:
        total = (await session.execute(count_stmt)).scalar_one()
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [FlowRead.model_validate(r).model_dump() for r in rows],
        "total": total,
    }


@router.get("/events")
async def list_events(
    event_type: Annotated[str | None, Query(description="Event type filter")] = None,
    entity_id: Annotated[uuid.UUID | None, Query(description="Linked entity UUID")] = None,
    bbox: Annotated[str | None, Query(description="Bounding box: west,south,east,north")] = None,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Query economic events."""
    stmt = select(Event)
    count_stmt = select(func.count()).select_from(Event)

    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
        count_stmt = count_stmt.where(Event.event_type == event_type)
    if entity_id:
        stmt = stmt.where(Event.entity_id == entity_id)
        count_stmt = count_stmt.where(Event.entity_id == entity_id)
    if bbox:
        w, s, e, n = [float(x) for x in bbox.split(",")]
        envelope = ST_MakeEnvelope(w, s, e, n, 4326)
        stmt = stmt.where(Event.geometry.ST_Intersects(envelope))
        count_stmt = count_stmt.where(Event.geometry.ST_Intersects(envelope))
    if time_start:
        stmt = stmt.where(Event.timestamp >= time_start)
        count_stmt = count_stmt.where(Event.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(Event.timestamp <= time_end)
        count_stmt = count_stmt.where(Event.timestamp <= time_end)

    stmt = stmt.order_by(Event.timestamp.desc()).offset(offset).limit(limit)

    async with async_session_factory() as session:
        total = (await session.execute(count_stmt)).scalar_one()
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [EventRead.model_validate(r).model_dump() for r in rows],
        "total": total,
    }


@router.get("/assessments")
async def list_assessments(
    assessor: Annotated[str | None, Query(description="Assessor name")] = None,
    metric_code: Annotated[str | None, Query(description="Metric code")] = None,
    entity_id: Annotated[uuid.UUID | None, Query(description="Entity UUID")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Query assessments."""
    stmt = select(Assessment)
    count_stmt = select(func.count()).select_from(Assessment)

    if assessor:
        stmt = stmt.where(Assessment.assessor == assessor)
        count_stmt = count_stmt.where(Assessment.assessor == assessor)
    if metric_code:
        stmt = stmt.where(Assessment.metric_code == metric_code)
        count_stmt = count_stmt.where(Assessment.metric_code == metric_code)
    if entity_id:
        stmt = stmt.where(Assessment.entity_id == entity_id)
        count_stmt = count_stmt.where(Assessment.entity_id == entity_id)

    stmt = stmt.offset(offset).limit(limit)

    async with async_session_factory() as session:
        total = (await session.execute(count_stmt)).scalar_one()
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [AssessmentRead.model_validate(r).model_dump() for r in rows],
        "total": total,
    }
