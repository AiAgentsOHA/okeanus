"""Streaming system status endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from okeanus.streaming.redis_pool import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/streaming", tags=["streaming"])

# Will be set by main.py lifespan
_scheduler = None


def set_scheduler(scheduler) -> None:
    global _scheduler
    _scheduler = scheduler


@router.get("/status")
async def streaming_status() -> dict[str, Any]:
    """Return status of streaming infrastructure."""
    redis_ok = False
    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    vessel_count = 0
    if redis_ok:
        try:
            r = await get_redis()
            vessel_count = await r.zcard("vessels:positions")
        except Exception:
            pass

    return {
        "redis": "connected" if redis_ok else "disconnected",
        "tracked_vessels": vessel_count,
        "scheduler": _scheduler.status() if _scheduler else [],
    }


@router.get("/vessels/nearby")
async def vessels_nearby(
    lon: float,
    lat: float,
    radius_km: float = 50,
) -> dict[str, Any]:
    """Get vessels near a point using Redis Geo Set."""
    r = await get_redis()
    results = await r.geosearch(
        "vessels:positions",
        longitude=lon,
        latitude=lat,
        radius=radius_km,
        unit="km",
        withcoord=True,
        withdist=True,
        sort="ASC",
        count=100,
    )

    vessels = []
    for item in results:
        mmsi = item[0] if isinstance(item, (list, tuple)) else item
        dist = item[1] if isinstance(item, (list, tuple)) and len(item) > 1 else None
        coord = item[2] if isinstance(item, (list, tuple)) and len(item) > 2 else None

        vessel_info = await r.hgetall(f"vessel:{mmsi}")
        vessels.append({
            "mmsi": mmsi,
            "distance_km": float(dist) if dist else None,
            "lon": float(coord[0]) if coord else None,
            "lat": float(coord[1]) if coord else None,
            **vessel_info,
        })

    return {"vessels": vessels, "total": len(vessels)}
