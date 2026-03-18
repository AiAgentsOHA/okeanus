"""Time series forecasting -- stub for Chronos integration."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from okeanus.db.postgres import async_session_factory
from okeanus.schema.economy import TimeSeries

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml/forecast", tags=["ml"])


@router.get("")
async def forecast_timeseries(
    code: Annotated[str, Query(description="Time series code to forecast")],
    horizon: Annotated[
        int, Query(ge=1, le=365, description="Forecast horizon in periods")
    ] = 30,
    time_start: Annotated[datetime | None, Query(description="Historical data start")] = None,
    time_end: Annotated[datetime | None, Query(description="Historical data end")] = None,
) -> dict[str, Any]:
    """Forecast future values for a time series.

    Currently uses simple exponential smoothing.
    Will be upgraded to Chronos-Bolt when torch dependencies are added.
    """
    stmt = select(TimeSeries.timestamp, TimeSeries.value).where(
        TimeSeries.code == code
    ).order_by(TimeSeries.timestamp)

    if time_start:
        stmt = stmt.where(TimeSeries.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(TimeSeries.timestamp <= time_end)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).all()

    if len(rows) < 10:
        return {"error": f"Not enough data points ({len(rows)}). Need at least 10."}

    values = [r.value for r in rows]
    timestamps = [r.timestamp for r in rows]

    # Simple exponential smoothing forecast
    alpha = 0.3
    smoothed = values[0]
    for v in values[1:]:
        smoothed = alpha * v + (1 - alpha) * smoothed

    # Estimate trend from last N points
    n = min(len(values), 30)
    recent = values[-n:]
    x_mean = (n - 1) / 2
    y_mean = sum(recent) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(recent))
    den = sum((i - x_mean) ** 2 for i in range(n))
    trend = num / den if den > 0 else 0

    # Generate forecast
    last_ts = timestamps[-1]
    # Estimate period from median time delta
    if len(timestamps) >= 2:
        deltas = [
            (timestamps[i] - timestamps[i - 1]).total_seconds()
            for i in range(1, len(timestamps))
        ]
        deltas.sort()
        median_delta_s = deltas[len(deltas) // 2]
    else:
        median_delta_s = 86400  # default 1 day

    # Calculate historical std for confidence intervals
    residuals = []
    s = values[0]
    for v in values[1:]:
        s = alpha * v + (1 - alpha) * s
        residuals.append(v - s)
    std = math.sqrt(sum(r**2 for r in residuals) / len(residuals)) if residuals else 0

    forecasts = []
    for i in range(1, horizon + 1):
        forecast_ts = last_ts + timedelta(seconds=median_delta_s * i)
        forecast_val = smoothed + trend * i
        forecasts.append({
            "timestamp": forecast_ts.isoformat(),
            "value": round(forecast_val, 4),
            "lower_95": round(forecast_val - 1.96 * std * math.sqrt(i), 4),
            "upper_95": round(forecast_val + 1.96 * std * math.sqrt(i), 4),
        })

    return {
        "code": code,
        "method": "exponential_smoothing",
        "historical_points": len(values),
        "horizon": horizon,
        "forecasts": forecasts,
        "note": (
            "Upgrade to Chronos-Bolt for probabilistic zero-shot forecasting "
            "by adding chronos-forecasting to ml dependencies."
        ),
    }
