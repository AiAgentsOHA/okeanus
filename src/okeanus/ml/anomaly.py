"""Anomaly detection -- z-score for time series, AIS gap detection."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation
from okeanus.schema.economy import TimeSeries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml/anomaly", tags=["ml"])


@router.get("/zscore")
async def timeseries_zscore(
    code: Annotated[str, Query(description="Time series code")],
    window: Annotated[int, Query(ge=5, le=365, description="Rolling window size")] = 30,
    threshold: Annotated[float, Query(ge=1.0, le=10.0, description="Z-score threshold")] = 3.0,
    time_start: Annotated[datetime | None, Query(description="Start time")] = None,
    time_end: Annotated[datetime | None, Query(description="End time")] = None,
) -> dict[str, Any]:
    """Detect anomalies in time series using rolling z-score."""
    stmt = select(TimeSeries.timestamp, TimeSeries.value).where(
        TimeSeries.code == code
    ).order_by(TimeSeries.timestamp)

    if time_start:
        stmt = stmt.where(TimeSeries.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(TimeSeries.timestamp <= time_end)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).all()

    if len(rows) < window:
        return {
            "anomalies": [],
            "message": f"Not enough data points ({len(rows)}) for window size {window}",
        }

    # Calculate rolling z-scores
    anomalies = []
    values = [r.value for r in rows]
    timestamps = [r.timestamp for r in rows]

    for i in range(window, len(values)):
        window_vals = values[i - window:i]
        mean = sum(window_vals) / len(window_vals)
        variance = sum((v - mean) ** 2 for v in window_vals) / len(window_vals)
        std = math.sqrt(variance) if variance > 0 else 0

        if std > 0:
            z = (values[i] - mean) / std
            if abs(z) >= threshold:
                anomalies.append({
                    "timestamp": timestamps[i].isoformat(),
                    "value": values[i],
                    "z_score": round(z, 3),
                    "rolling_mean": round(mean, 3),
                    "rolling_std": round(std, 3),
                    "direction": "spike" if z > 0 else "drop",
                })

    return {
        "code": code,
        "window": window,
        "threshold": threshold,
        "total_points": len(values),
        "anomalies": anomalies,
        "anomaly_count": len(anomalies),
    }


@router.get("/ais-gaps")
async def ais_gaps(
    mmsi: Annotated[str | None, Query(description="Filter by MMSI")] = None,
    gap_hours: Annotated[
        float, Query(ge=1, le=168, description="Minimum gap in hours")
    ] = 6.0,
    time_start: Annotated[datetime | None, Query(description="Start time")] = None,
    time_end: Annotated[datetime | None, Query(description="End time")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, Any]:
    """Detect AIS transmission gaps (potential dark activity)."""
    stmt = select(
        Observation.mmsi,
        Observation.timestamp,
        Observation.geometry,
    ).where(
        Observation.obs_type == "vessel",
        Observation.mmsi.isnot(None),
    ).order_by(Observation.mmsi, Observation.timestamp)

    if mmsi:
        stmt = stmt.where(Observation.mmsi == int(mmsi))
    if time_start:
        stmt = stmt.where(Observation.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(Observation.timestamp <= time_end)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).all()

    # Detect gaps per vessel
    gaps: list[dict[str, Any]] = []
    gap_threshold = timedelta(hours=gap_hours)
    prev_mmsi = None
    prev_ts = None

    for row in rows:
        if row.mmsi == prev_mmsi and prev_ts:
            delta = row.timestamp - prev_ts
            if delta >= gap_threshold:
                gaps.append({
                    "mmsi": str(row.mmsi),
                    "gap_start": prev_ts.isoformat(),
                    "gap_end": row.timestamp.isoformat(),
                    "gap_hours": round(delta.total_seconds() / 3600, 1),
                })
        prev_mmsi = row.mmsi
        prev_ts = row.timestamp

    # Sort by gap duration descending
    gaps.sort(key=lambda g: g["gap_hours"], reverse=True)

    return {
        "gap_threshold_hours": gap_hours,
        "gaps": gaps[:limit],
        "total_gaps": len(gaps),
    }
