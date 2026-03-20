"""WebSocket endpoint for real-time vessel tracking."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from okeanus.config import settings
from okeanus.streaming.redis_pool import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["streaming"])


class VesselConnectionManager:
    """Manages WebSocket connections and their bbox subscriptions."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, dict[str, Any]] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[ws] = {"bbox": None}
        logger.info("Vessel WebSocket connected, total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.pop(ws, None)
        logger.info("Vessel WebSocket disconnected, total: %d", len(self._connections))

    def set_bbox(self, ws: WebSocket, bbox: list[float]) -> None:
        if ws in self._connections:
            self._connections[ws]["bbox"] = bbox

    def in_bbox(self, ws: WebSocket, lon: float, lat: float) -> bool:
        info = self._connections.get(ws)
        if not info or not info["bbox"]:
            return True  # No filter = receive all
        west, south, east, north = info["bbox"]
        return west <= lon <= east and south <= lat <= north

    @property
    def active_connections(self) -> list[WebSocket]:
        return list(self._connections.keys())


manager = VesselConnectionManager()


@router.websocket("/ws/vessels")
async def vessel_stream(ws: WebSocket) -> None:
    """WebSocket endpoint for real-time vessel positions.

    Client sends: {"subscribe": "vessels", "bbox": [west, south, east, north]}
    Server sends: {"mmsi": "...", "lat": ..., "lon": ..., "sog": ..., ...}
    """
    await manager.connect(ws)

    # Background task to listen to Redis pub/sub
    redis_task = asyncio.create_task(_redis_listener(ws))
    heartbeat_task = asyncio.create_task(_heartbeat(ws))

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if "bbox" in msg:
                    manager.set_bbox(ws, msg["bbox"])
                    await ws.send_json({"status": "subscribed", "bbox": msg["bbox"]})
            except json.JSONDecodeError:
                await ws.send_json({"error": "Invalid JSON"})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)
        redis_task.cancel()
        heartbeat_task.cancel()
        try:
            await redis_task
        except asyncio.CancelledError:
            pass
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


async def _redis_listener(ws: WebSocket) -> None:
    """Subscribe to Redis vessel updates and forward to WebSocket client."""
    try:
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe("vessels:updates")

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                position = json.loads(message["data"])
                lon = position.get("lon", 0)
                lat = position.get("lat", 0)
                if manager.in_bbox(ws, lon, lat):
                    await ws.send_json(position)
            except Exception:
                pass
    except asyncio.CancelledError:
        await pubsub.unsubscribe("vessels:updates")
        await pubsub.aclose()
    except Exception as exc:
        logger.error("Redis listener error: %s", exc)


async def _heartbeat(ws: WebSocket) -> None:
    """Send periodic heartbeat to keep connection alive."""
    try:
        while True:
            await asyncio.sleep(settings.websocket_heartbeat_seconds)
            await ws.send_json({"type": "heartbeat"})
    except (asyncio.CancelledError, Exception):
        pass
