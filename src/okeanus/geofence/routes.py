"""Geofence CRUD endpoints + alert queries + batch evaluation."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, update

from okeanus.db.postgres import async_session_factory
from okeanus.geofence.engine import GeofenceEngine, ZoneConfig, get_geofence_engine
from okeanus.geofence.models import (
    AlertRead,
    GeofenceAlert,
    GeofenceRule,
    GeofenceZone,
    RuleCreate,
    RuleRead,
    ZoneCreate,
    ZoneRead,
    ZoneUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/geofence", tags=["geofence"])


# ---------------------------------------------------------------------------
# Zone CRUD
# ---------------------------------------------------------------------------


@router.post("/zones", response_model=ZoneRead, status_code=201)
async def create_zone(body: ZoneCreate) -> ZoneRead:
    """Create a new geofence zone."""
    zone = GeofenceZone(
        name=body.name,
        description=body.description,
        zone_type=body.zone_type.value,
        geometry_data=body.geometry_data,
        category=body.category,
        metadata_=body.metadata,
    )
    async with async_session_factory() as session:
        session.add(zone)
        await session.commit()
        await session.refresh(zone)

    # Update in-memory engine
    await _refresh_engine_zone(zone)

    return ZoneRead.model_validate(zone)


@router.get("/zones", response_model=list[ZoneRead])
async def list_zones(
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    active_only: Annotated[bool, Query(description="Only active zones")] = True,
) -> list[ZoneRead]:
    """List all geofence zones."""
    stmt = select(GeofenceZone)
    if active_only:
        stmt = stmt.where(GeofenceZone.is_active.is_(True))
    if category:
        stmt = stmt.where(GeofenceZone.category == category)
    stmt = stmt.order_by(GeofenceZone.created_at.desc())

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return [ZoneRead.model_validate(z) for z in rows]


@router.get("/zones/{zone_id}", response_model=ZoneRead)
async def get_zone(zone_id: uuid.UUID) -> ZoneRead:
    """Get a specific geofence zone."""
    async with async_session_factory() as session:
        zone = await session.get(GeofenceZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return ZoneRead.model_validate(zone)


@router.patch("/zones/{zone_id}", response_model=ZoneRead)
async def update_zone(zone_id: uuid.UUID, body: ZoneUpdate) -> ZoneRead:
    """Update a geofence zone."""
    async with async_session_factory() as session:
        zone = await session.get(GeofenceZone, zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

        if body.name is not None:
            zone.name = body.name
        if body.description is not None:
            zone.description = body.description
        if body.is_active is not None:
            zone.is_active = body.is_active
        if body.category is not None:
            zone.category = body.category

        await session.commit()
        await session.refresh(zone)

    # Update in-memory engine
    if body.is_active is False:
        get_geofence_engine().remove_zone(str(zone_id))
    else:
        await _refresh_engine_zone(zone)

    return ZoneRead.model_validate(zone)


@router.delete("/zones/{zone_id}", status_code=204)
async def delete_zone(zone_id: uuid.UUID) -> None:
    """Deactivate a geofence zone (soft delete)."""
    async with async_session_factory() as session:
        zone = await session.get(GeofenceZone, zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        zone.is_active = False
        await session.commit()

    get_geofence_engine().remove_zone(str(zone_id))


# ---------------------------------------------------------------------------
# Rule CRUD
# ---------------------------------------------------------------------------


@router.post("/rules", response_model=RuleRead, status_code=201)
async def create_rule(body: RuleCreate) -> RuleRead:
    """Create a new geofence monitoring rule."""
    # Verify zone exists
    async with async_session_factory() as session:
        zone = await session.get(GeofenceZone, body.zone_id)
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")

    rule = GeofenceRule(
        zone_id=body.zone_id,
        rule_type=body.rule_type.value,
        severity=body.severity.value,
        parameters=body.parameters,
        vessel_filter=body.vessel_filter,
    )
    async with async_session_factory() as session:
        session.add(rule)
        await session.commit()
        await session.refresh(rule)

    # Refresh the zone in the engine
    await _refresh_engine_zone_by_id(str(body.zone_id))

    return RuleRead.model_validate(rule)


@router.get("/rules", response_model=list[RuleRead])
async def list_rules(
    zone_id: Annotated[uuid.UUID | None, Query(description="Filter by zone")] = None,
) -> list[RuleRead]:
    """List geofence rules."""
    stmt = select(GeofenceRule).where(GeofenceRule.is_active.is_(True))
    if zone_id:
        stmt = stmt.where(GeofenceRule.zone_id == zone_id)
    stmt = stmt.order_by(GeofenceRule.created_at.desc())

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return [RuleRead.model_validate(r) for r in rows]


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: uuid.UUID) -> None:
    """Deactivate a geofence rule."""
    async with async_session_factory() as session:
        rule = await session.get(GeofenceRule, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        rule.is_active = False
        zone_id = str(rule.zone_id)
        await session.commit()

    await _refresh_engine_zone_by_id(zone_id)


# ---------------------------------------------------------------------------
# Alert queries
# ---------------------------------------------------------------------------


@router.get("/alerts", response_model=list[AlertRead])
async def list_alerts(
    zone_id: Annotated[uuid.UUID | None, Query(description="Filter by zone")] = None,
    mmsi: Annotated[int | None, Query(description="Filter by MMSI")] = None,
    severity: Annotated[str | None, Query(description="Filter by severity")] = None,
    rule_type: Annotated[str | None, Query(description="Filter by rule type")] = None,
    time_start: Annotated[datetime | None, Query(description="Start time")] = None,
    time_end: Annotated[datetime | None, Query(description="End time")] = None,
    unacknowledged_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[AlertRead]:
    """Query geofence alerts with filters."""
    stmt = select(GeofenceAlert)

    if zone_id:
        stmt = stmt.where(GeofenceAlert.zone_id == zone_id)
    if mmsi:
        stmt = stmt.where(GeofenceAlert.mmsi == mmsi)
    if severity:
        stmt = stmt.where(GeofenceAlert.severity == severity)
    if rule_type:
        stmt = stmt.where(GeofenceAlert.rule_type == rule_type)
    if time_start:
        stmt = stmt.where(GeofenceAlert.triggered_at >= time_start)
    if time_end:
        stmt = stmt.where(GeofenceAlert.triggered_at <= time_end)
    if unacknowledged_only:
        stmt = stmt.where(GeofenceAlert.is_acknowledged.is_(False))

    stmt = stmt.order_by(GeofenceAlert.triggered_at.desc()).limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return [AlertRead.model_validate(a) for a in rows]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: uuid.UUID) -> dict[str, Any]:
    """Acknowledge a geofence alert."""
    async with async_session_factory() as session:
        alert = await session.get(GeofenceAlert, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.is_acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        await session.commit()

    return {"status": "acknowledged", "alert_id": str(alert_id)}


@router.get("/alerts/summary")
async def alert_summary(
    time_start: Annotated[datetime | None, Query(description="Start time")] = None,
    time_end: Annotated[datetime | None, Query(description="End time")] = None,
) -> dict[str, Any]:
    """Get alert statistics grouped by severity and rule type."""
    stmt = select(GeofenceAlert)
    if time_start:
        stmt = stmt.where(GeofenceAlert.triggered_at >= time_start)
    if time_end:
        stmt = stmt.where(GeofenceAlert.triggered_at <= time_end)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    by_severity: dict[str, int] = {}
    by_rule_type: dict[str, int] = {}
    by_zone: dict[str, int] = {}
    unacknowledged = 0

    for a in rows:
        by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
        by_rule_type[a.rule_type] = by_rule_type.get(a.rule_type, 0) + 1
        zone_key = str(a.zone_id)
        by_zone[zone_key] = by_zone.get(zone_key, 0) + 1
        if not a.is_acknowledged:
            unacknowledged += 1

    return {
        "total_alerts": len(rows),
        "unacknowledged": unacknowledged,
        "by_severity": by_severity,
        "by_rule_type": by_rule_type,
        "by_zone": by_zone,
    }


# ---------------------------------------------------------------------------
# Evaluation endpoints
# ---------------------------------------------------------------------------


@router.post("/evaluate")
async def evaluate_position(
    body: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a single vessel position against all active geofence zones.

    Body: {"mmsi": int, "lat": float, "lon": float, "sog": float, "timestamp": str}

    Returns any alerts triggered by this position.
    """
    engine = get_geofence_engine()
    ts = datetime.fromisoformat(body["timestamp"]) if isinstance(body.get("timestamp"), str) else body.get("timestamp", datetime.utcnow())

    alerts = engine.evaluate(
        mmsi=body["mmsi"],
        lat=body["lat"],
        lon=body["lon"],
        sog=body.get("sog", 0.0),
        timestamp=ts,
    )

    # Persist alerts
    if alerts:
        async with async_session_factory() as session:
            for a in alerts:
                session.add(GeofenceAlert(
                    zone_id=uuid.UUID(a.zone_id),
                    rule_id=uuid.UUID(a.rule_id),
                    mmsi=a.mmsi,
                    rule_type=a.rule_type,
                    severity=a.severity,
                    triggered_at=a.triggered_at,
                    lat=a.lat,
                    lon=a.lon,
                    details=a.details,
                ))
            await session.commit()

    return {
        "alerts_triggered": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.post("/evaluate/batch")
async def evaluate_batch(
    body: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate a batch of vessel positions against all active geofence zones.

    Body: {"positions": [{"mmsi": int, "lat": float, "lon": float, "sog": float, "timestamp": str}, ...]}
    """
    engine = get_geofence_engine()
    positions = body.get("positions", [])

    # Parse timestamps
    parsed = []
    for pos in positions:
        ts = pos.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        elif ts is None:
            ts = datetime.utcnow()
        parsed.append({**pos, "timestamp": ts})

    alerts = engine.evaluate_batch(parsed)

    # Persist alerts
    if alerts:
        async with async_session_factory() as session:
            for a in alerts:
                session.add(GeofenceAlert(
                    zone_id=uuid.UUID(a.zone_id),
                    rule_id=uuid.UUID(a.rule_id),
                    mmsi=a.mmsi,
                    rule_type=a.rule_type,
                    severity=a.severity,
                    triggered_at=a.triggered_at,
                    lat=a.lat,
                    lon=a.lon,
                    details=a.details,
                ))
            await session.commit()

    return {
        "positions_evaluated": len(positions),
        "alerts_triggered": len(alerts),
        "alerts": [a.to_dict() for a in alerts],
    }


@router.get("/vessel/{mmsi}/state")
async def vessel_zone_state(mmsi: int) -> dict[str, Any]:
    """Get current geofence zone state for a vessel."""
    engine = get_geofence_engine()
    return {
        "mmsi": str(mmsi),
        "zones": engine.get_state(mmsi),
    }


@router.post("/engine/reload")
async def reload_engine() -> dict[str, Any]:
    """Reload all active zones and rules into the geofence engine."""
    count = await _load_all_zones()
    return {"status": "reloaded", "zones_loaded": count}


# ---------------------------------------------------------------------------
# Engine management helpers
# ---------------------------------------------------------------------------


async def _load_all_zones() -> int:
    """Load all active zones with their rules into the engine."""
    engine = get_geofence_engine()

    async with async_session_factory() as session:
        zones = (await session.execute(
            select(GeofenceZone).where(GeofenceZone.is_active.is_(True))
        )).scalars().all()

        zone_configs: list[ZoneConfig] = []
        for z in zones:
            rules = (await session.execute(
                select(GeofenceRule).where(
                    GeofenceRule.zone_id == z.id,
                    GeofenceRule.is_active.is_(True),
                )
            )).scalars().all()

            zone_configs.append(ZoneConfig(
                id=str(z.id),
                name=z.name,
                zone_type=z.zone_type,
                geometry_data=z.geometry_data,
                rules=[{
                    "id": str(r.id),
                    "rule_type": r.rule_type,
                    "severity": r.severity,
                    "parameters": r.parameters,
                    "vessel_filter": r.vessel_filter,
                } for r in rules],
            ))

    engine.load_zones(zone_configs)
    return len(zone_configs)


async def _refresh_engine_zone(zone: GeofenceZone) -> None:
    """Refresh a single zone in the engine."""
    engine = get_geofence_engine()

    async with async_session_factory() as session:
        rules = (await session.execute(
            select(GeofenceRule).where(
                GeofenceRule.zone_id == zone.id,
                GeofenceRule.is_active.is_(True),
            )
        )).scalars().all()

    engine.add_zone(ZoneConfig(
        id=str(zone.id),
        name=zone.name,
        zone_type=zone.zone_type,
        geometry_data=zone.geometry_data,
        rules=[{
            "id": str(r.id),
            "rule_type": r.rule_type,
            "severity": r.severity,
            "parameters": r.parameters,
            "vessel_filter": r.vessel_filter,
        } for r in rules],
    ))


async def _refresh_engine_zone_by_id(zone_id: str) -> None:
    """Refresh a zone by ID."""
    async with async_session_factory() as session:
        zone = await session.get(GeofenceZone, uuid.UUID(zone_id))
    if zone and zone.is_active:
        await _refresh_engine_zone(zone)
    else:
        get_geofence_engine().remove_zone(zone_id)
