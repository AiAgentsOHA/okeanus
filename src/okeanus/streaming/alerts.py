"""Server-Sent Events endpoint for real-time alerts."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Query
from sse_starlette.sse import EventSourceResponse

from okeanus.streaming.redis_pool import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["streaming"])


@router.get("/events/alerts")
async def alert_stream(
    types: Annotated[
        str | None, Query(description="Comma-separated alert types")
    ] = None,
    severity: Annotated[
        str | None, Query(description="Comma-separated severity levels")
    ] = None,
) -> EventSourceResponse:
    """SSE stream of real-time alerts.

    Filters:
    - types: ais_gap, mpa_violation, price_spike, sensor_anomaly
    - severity: low, medium, high, critical
    """
    type_filter = set(types.split(",")) if types else None
    severity_filter = set(severity.split(",")) if severity else None

    async def event_generator():
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe("alerts:stream")

        try:
            while True:
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=15.0,
                )
                if message is None:
                    # Send heartbeat comment to prevent proxy timeouts
                    yield {"comment": "heartbeat"}
                    continue

                if message["type"] != "message":
                    continue

                try:
                    alert = json.loads(message["data"])
                    # Apply filters
                    if type_filter and alert.get("alert_type") not in type_filter:
                        continue
                    if severity_filter and alert.get("severity") not in severity_filter:
                        continue
                    yield {
                        "event": alert.get("alert_type", "alert"),
                        "data": json.dumps(alert),
                    }
                except Exception:
                    pass
        except asyncio.CancelledError:
            await pubsub.unsubscribe("alerts:stream")
            await pubsub.aclose()

    return EventSourceResponse(event_generator())
