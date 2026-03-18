"""Cross-source query endpoints -- joins across economy tables and observations."""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from geoalchemy2.functions import ST_DWithin, ST_MakeEnvelope, ST_SetSRID, ST_MakePoint
from sqlalchemy import func, select, and_, or_, cast, Float as SAFloat
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation, ObservationBase
from okeanus.schema.economy import (
    Assessment, AssessmentRead,
    Entity, EntityRead,
    Event, EventRead,
    Flow, FlowRead,
    Relationship, RelationshipRead,
    TimeSeries, TimeSeriesRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["query"])


# ---------------------------------------------------------------------------
# Endpoint 1: Entity context -- entity + all linked data + nearby obs
# ---------------------------------------------------------------------------

@router.get("/entity-context/{entity_id}")
async def entity_context(
    entity_id: uuid.UUID,
    include_assessments: Annotated[bool, Query(description="Include linked assessments")] = True,
    include_flows: Annotated[bool, Query(description="Include linked flows")] = True,
    include_relationships: Annotated[bool, Query(description="Include linked relationships")] = True,
    include_events: Annotated[bool, Query(description="Include linked events")] = True,
    include_timeseries: Annotated[bool, Query(description="Include linked time series")] = True,
    include_observations: Annotated[bool, Query(description="Include nearby observations")] = False,
    observation_radius_km: Annotated[float, Query(ge=0.1, le=500, description="Radius in km for nearby observations")] = 50,
    observation_types: Annotated[str | None, Query(description="Comma-separated obs_type filter")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """Return an entity with all linked data across economy tables and nearby observations."""
    async with async_session_factory() as session:
        # Fetch entity
        entity = (
            await session.execute(select(Entity).where(Entity.id == entity_id))
        ).scalar_one_or_none()
        if entity is None:
            raise HTTPException(status_code=404, detail="Entity not found")

        result: dict[str, Any] = {
            "entity": EntityRead.model_validate(entity).model_dump(),
        }

        if include_assessments:
            rows = (await session.execute(
                select(Assessment)
                .where(Assessment.entity_id == entity_id)
                .limit(limit)
            )).scalars().all()
            result["assessments"] = [AssessmentRead.model_validate(r).model_dump() for r in rows]

        if include_flows:
            rows = (await session.execute(
                select(Flow)
                .where(or_(
                    Flow.source_entity_id == entity_id,
                    Flow.dest_entity_id == entity_id,
                ))
                .limit(limit)
            )).scalars().all()
            result["flows"] = [FlowRead.model_validate(r).model_dump() for r in rows]

        if include_relationships:
            rows = (await session.execute(
                select(Relationship)
                .where(or_(
                    Relationship.source_entity_id == entity_id,
                    Relationship.dest_entity_id == entity_id,
                ))
                .limit(limit)
            )).scalars().all()
            result["relationships"] = [RelationshipRead.model_validate(r).model_dump() for r in rows]

        if include_events:
            rows = (await session.execute(
                select(Event)
                .where(Event.entity_id == entity_id)
                .limit(limit)
            )).scalars().all()
            result["events"] = [EventRead.model_validate(r).model_dump() for r in rows]

        if include_timeseries:
            rows = (await session.execute(
                select(TimeSeries)
                .where(TimeSeries.entity_id == entity_id)
                .order_by(TimeSeries.timestamp.desc())
                .limit(limit)
            )).scalars().all()
            result["timeseries"] = [TimeSeriesRead.model_validate(r).model_dump() for r in rows]

        if include_observations and entity.geometry is not None:
            # Convert km to approximate degrees (1 degree ~ 111.32 km)
            radius_degrees = observation_radius_km / 111.32
            stmt = (
                select(Observation)
                .where(ST_DWithin(
                    Observation.geometry,
                    entity.geometry,
                    radius_degrees,
                ))
                .limit(limit)
            )
            if observation_types:
                type_list = [t.strip() for t in observation_types.split(",")]
                stmt = stmt.where(Observation.obs_type.in_(type_list))
            rows = (await session.execute(stmt)).scalars().all()
            result["observations"] = [ObservationBase.model_validate(r).model_dump() for r in rows]

    return result


# ---------------------------------------------------------------------------
# Endpoint 2: Unified spatial query across all domain tables
# ---------------------------------------------------------------------------

@router.get("/spatial")
async def spatial_query(
    bbox: Annotated[str, Query(description="Bounding box: west,south,east,north")],
    entity_types: Annotated[str | None, Query(description="Comma-separated entity type filter")] = None,
    obs_types: Annotated[str | None, Query(description="Comma-separated obs_type filter")] = None,
    include_timeseries: Annotated[bool, Query(description="Include time series in bbox")] = True,
    include_events: Annotated[bool, Query(description="Include events in bbox")] = True,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    """Unified bbox query across entities, observations, time series, and events."""
    try:
        w, s, e, n = [float(x) for x in bbox.split(",")]
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid bbox format. Expected: west,south,east,north")

    envelope = ST_MakeEnvelope(w, s, e, n, 4326)

    async with async_session_factory() as session:
        result: dict[str, Any] = {}

        # Entities in bbox
        entity_stmt = (
            select(Entity)
            .where(Entity.geometry.ST_Intersects(envelope))
            .limit(limit)
        )
        if entity_types:
            type_list = [t.strip() for t in entity_types.split(",")]
            entity_stmt = entity_stmt.where(Entity.entity_type.in_(type_list))
        rows = (await session.execute(entity_stmt)).scalars().all()
        result["entities"] = [EntityRead.model_validate(r).model_dump() for r in rows]

        # Observations in bbox
        obs_stmt = (
            select(Observation)
            .where(Observation.geometry.ST_Intersects(envelope))
            .limit(limit)
        )
        if obs_types:
            type_list = [t.strip() for t in obs_types.split(",")]
            obs_stmt = obs_stmt.where(Observation.obs_type.in_(type_list))
        if time_start:
            obs_stmt = obs_stmt.where(Observation.timestamp >= time_start)
        if time_end:
            obs_stmt = obs_stmt.where(Observation.timestamp <= time_end)
        rows = (await session.execute(obs_stmt)).scalars().all()
        result["observations"] = [ObservationBase.model_validate(r).model_dump() for r in rows]

        # TimeSeries in bbox
        if include_timeseries:
            ts_stmt = (
                select(TimeSeries)
                .where(TimeSeries.geometry.ST_Intersects(envelope))
                .limit(limit)
            )
            if time_start:
                ts_stmt = ts_stmt.where(TimeSeries.timestamp >= time_start)
            if time_end:
                ts_stmt = ts_stmt.where(TimeSeries.timestamp <= time_end)
            rows = (await session.execute(ts_stmt)).scalars().all()
            result["timeseries"] = [TimeSeriesRead.model_validate(r).model_dump() for r in rows]

        # Events in bbox
        if include_events:
            ev_stmt = (
                select(Event)
                .where(Event.geometry.ST_Intersects(envelope))
                .limit(limit)
            )
            if time_start:
                ev_stmt = ev_stmt.where(Event.timestamp >= time_start)
            if time_end:
                ev_stmt = ev_stmt.where(Event.timestamp <= time_end)
            rows = (await session.execute(ev_stmt)).scalars().all()
            result["events"] = [EventRead.model_validate(r).model_dump() for r in rows]

    return result


# ---------------------------------------------------------------------------
# Endpoint 3: Entity network -- BFS graph traversal
# ---------------------------------------------------------------------------

@router.get("/entity-network/{entity_id}")
async def entity_network(
    entity_id: uuid.UUID,
    depth: Annotated[int, Query(ge=1, le=3, description="BFS depth (max 3)")] = 1,
    relationship_types: Annotated[str | None, Query(description="Comma-separated relationship type filter")] = None,
    include_assessments: Annotated[bool, Query(description="Include assessments for each entity")] = True,
) -> dict[str, Any]:
    """BFS graph traversal via relationships and flows from a seed entity."""
    async with async_session_factory() as session:
        # Verify seed entity exists
        seed = (
            await session.execute(select(Entity).where(Entity.id == entity_id))
        ).scalar_one_or_none()
        if seed is None:
            raise HTTPException(status_code=404, detail="Entity not found")

        visited: set[uuid.UUID] = {entity_id}
        frontier: set[uuid.UUID] = {entity_id}
        all_rel_edges: list[dict] = []
        all_flow_edges: list[dict] = []

        for _level in range(depth):
            if not frontier:
                break

            frontier_list = list(frontier)

            # Query relationships from frontier
            rel_stmt = select(Relationship).where(or_(
                Relationship.source_entity_id.in_(frontier_list),
                Relationship.dest_entity_id.in_(frontier_list),
            ))
            if relationship_types:
                type_list = [t.strip() for t in relationship_types.split(",")]
                rel_stmt = rel_stmt.where(Relationship.relationship_type.in_(type_list))
            rels = (await session.execute(rel_stmt)).scalars().all()

            # Query flows from frontier
            flow_stmt = select(Flow).where(or_(
                Flow.source_entity_id.in_(frontier_list),
                Flow.dest_entity_id.in_(frontier_list),
            ))
            flows = (await session.execute(flow_stmt)).scalars().all()

            # Collect edges and discover new entity IDs
            next_frontier: set[uuid.UUID] = set()
            for rel in rels:
                all_rel_edges.append({
                    "type": "relationship",
                    "relationship_type": rel.relationship_type,
                    "source_id": str(rel.source_entity_id),
                    "dest_id": str(rel.dest_entity_id),
                    "strength": rel.strength,
                    "status": rel.status,
                })
                for eid in (rel.source_entity_id, rel.dest_entity_id):
                    if eid not in visited:
                        visited.add(eid)
                        next_frontier.add(eid)

            for flow in flows:
                edge: dict[str, Any] = {
                    "type": "flow",
                    "flow_type": flow.flow_type,
                    "source_id": str(flow.source_entity_id) if flow.source_entity_id else None,
                    "dest_id": str(flow.dest_entity_id) if flow.dest_entity_id else None,
                    "amount": flow.amount,
                    "currency": flow.currency,
                    "commodity": flow.commodity,
                }
                all_flow_edges.append(edge)
                for eid in (flow.source_entity_id, flow.dest_entity_id):
                    if eid is not None and eid not in visited:
                        visited.add(eid)
                        next_frontier.add(eid)

            frontier = next_frontier

        # Batch fetch all discovered entities
        entity_list = list(visited)
        entities_result = (
            await session.execute(select(Entity).where(Entity.id.in_(entity_list)))
        ).scalars().all()
        entity_map = {e.id: e for e in entities_result}

        # Optionally batch fetch assessments for all entities
        assessment_map: dict[uuid.UUID, list[dict]] = {}
        if include_assessments:
            assessments = (
                await session.execute(
                    select(Assessment).where(Assessment.entity_id.in_(entity_list))
                )
            ).scalars().all()
            for a in assessments:
                if a.entity_id not in assessment_map:
                    assessment_map[a.entity_id] = []
                assessment_map[a.entity_id].append(
                    AssessmentRead.model_validate(a).model_dump()
                )

        # Build nodes
        nodes = []
        for eid in entity_list:
            entity = entity_map.get(eid)
            if entity is None:
                continue
            node: dict[str, Any] = {
                "entity": EntityRead.model_validate(entity).model_dump(),
            }
            if include_assessments:
                node["assessments"] = assessment_map.get(eid, [])
            nodes.append(node)

    return {
        "nodes": nodes,
        "edges": all_rel_edges + all_flow_edges,
    }


# ---------------------------------------------------------------------------
# Endpoint 4: Temporal correlation between observations and time series
# ---------------------------------------------------------------------------

@router.get("/correlate")
async def correlate(
    obs_type: Annotated[str, Query(description="Observation type to aggregate")],
    ts_code: Annotated[str, Query(description="Time series code to aggregate")],
    bbox: Annotated[str | None, Query(description="Bounding box: west,south,east,north")] = None,
    aggregation: Annotated[str, Query(description="Time bucket: hour, day, week, month")] = "day",
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> dict[str, Any]:
    """Temporal correlation between observation quality scores and time series values."""
    valid_aggs = {"hour", "day", "week", "month"}
    if aggregation not in valid_aggs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid aggregation. Must be one of: {', '.join(sorted(valid_aggs))}",
        )

    async with async_session_factory() as session:
        # Aggregate observations by time bucket
        obs_stmt = (
            select(
                func.date_trunc(aggregation, Observation.timestamp).label("period"),
                func.avg(Observation.quality_score).label("obs_avg"),
                func.count().label("obs_count"),
            )
            .where(Observation.obs_type == obs_type)
            .group_by(func.date_trunc(aggregation, Observation.timestamp))
        )
        if time_start:
            obs_stmt = obs_stmt.where(Observation.timestamp >= time_start)
        if time_end:
            obs_stmt = obs_stmt.where(Observation.timestamp <= time_end)
        if bbox:
            try:
                w, s, e, n = [float(x) for x in bbox.split(",")]
            except (ValueError, AttributeError):
                raise HTTPException(status_code=400, detail="Invalid bbox format")
            envelope = ST_MakeEnvelope(w, s, e, n, 4326)
            obs_stmt = obs_stmt.where(Observation.geometry.ST_Intersects(envelope))

        obs_rows = (await session.execute(obs_stmt)).all()
        obs_by_period = {row.period: {"obs_avg": float(row.obs_avg) if row.obs_avg is not None else None,
                                       "obs_count": row.obs_count}
                         for row in obs_rows}

        # Aggregate time series by time bucket
        ts_stmt = (
            select(
                func.date_trunc(aggregation, TimeSeries.timestamp).label("period"),
                func.avg(TimeSeries.value).label("ts_avg"),
                func.count().label("ts_count"),
            )
            .where(TimeSeries.code == ts_code)
            .group_by(func.date_trunc(aggregation, TimeSeries.timestamp))
        )
        if time_start:
            ts_stmt = ts_stmt.where(TimeSeries.timestamp >= time_start)
        if time_end:
            ts_stmt = ts_stmt.where(TimeSeries.timestamp <= time_end)

        ts_rows = (await session.execute(ts_stmt)).all()
        ts_by_period = {row.period: {"ts_avg": float(row.ts_avg) if row.ts_avg is not None else None,
                                      "ts_count": row.ts_count}
                        for row in ts_rows}

    # Align on common periods
    common_periods = sorted(set(obs_by_period.keys()) & set(ts_by_period.keys()))
    aligned_data = []
    obs_vals = []
    ts_vals = []
    for period in common_periods:
        obs_avg = obs_by_period[period]["obs_avg"]
        ts_avg = ts_by_period[period]["ts_avg"]
        if obs_avg is not None and ts_avg is not None:
            obs_vals.append(obs_avg)
            ts_vals.append(ts_avg)
        aligned_data.append({
            "period": period.isoformat(),
            "obs_avg": obs_avg,
            "ts_avg": ts_avg,
        })

    # Calculate Pearson r
    pearson_r = None
    sample_size = len(obs_vals)
    if sample_size >= 2:
        obs_mean = sum(obs_vals) / sample_size
        ts_mean = sum(ts_vals) / sample_size
        numerator = sum((o - obs_mean) * (t - ts_mean) for o, t in zip(obs_vals, ts_vals))
        obs_var = sum((o - obs_mean) ** 2 for o in obs_vals)
        ts_var = sum((t - ts_mean) ** 2 for t in ts_vals)
        denominator = math.sqrt(obs_var * ts_var)
        if denominator > 0:
            pearson_r = numerator / denominator

    return {
        "aligned_data": aligned_data,
        "pearson_r": pearson_r,
        "sample_size": sample_size,
    }
