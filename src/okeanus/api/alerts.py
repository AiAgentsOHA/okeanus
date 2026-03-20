"""Alert management API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from okeanus.db.postgres import get_session
from okeanus.ml.alerting import AlertEngine
from okeanus.schema.economy import AlertRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])

_engine = AlertEngine()


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    status: str | None = Query(None, description="Filter by status: NEW, ACKNOWLEDGED, RESOLVED"),
    severity: str | None = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    alert_type: str | None = Query(None, description="Filter by type: ANOMALY, CHANGE_POINT, PATTERN"),
    limit: int = Query(50, ge=1, le=500),
) -> list[AlertRead]:
    """List alerts with optional filters."""
    async with get_session() as session:
        alerts = await _engine.get_alerts(
            session, status=status, severity=severity,
            alert_type=alert_type, limit=limit,
        )
        return [AlertRead.model_validate(a) for a in alerts]


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(alert_id: uuid.UUID) -> AlertRead:
    """Get a single alert by ID."""
    async with get_session() as session:
        from sqlalchemy import select
        from okeanus.schema.economy import Alert

        result = await session.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        return AlertRead.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertRead)
async def update_alert(
    alert_id: uuid.UUID,
    status: str = Query(..., description="New status: ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE"),
    resolved_by: str | None = Query(None, description="Who resolved it"),
) -> AlertRead:
    """Acknowledge or resolve an alert."""
    valid_statuses = {"ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    async with get_session() as session:
        alert = await _engine.acknowledge_alert(session, alert_id, resolved_by=resolved_by)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.status = status
        await session.commit()
        return AlertRead.model_validate(alert)


@router.post("/scan")
async def trigger_scan() -> dict[str, Any]:
    """Trigger a full anomaly scan across all data."""
    async with get_session() as session:
        counts = await _engine.run_full_scan(session)
        return {"status": "ok", "alerts_created": counts}
