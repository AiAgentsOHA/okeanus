"""AIS WebSocket ingester -- connects to AISStream.io and buffers positions."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import websockets

from okeanus.config import settings
from okeanus.streaming.redis_pool import get_redis

logger = logging.getLogger(__name__)


class AISIngester:
    """Background task that connects to AISStream WebSocket and writes to Redis."""

    def __init__(self) -> None:
        self._running = False
        self._buffer: list[dict] = []
        self._flush_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the AIS stream ingestion loop."""
        if not settings.ais_stream_api_key:
            logger.warning("AIS stream API key not set, skipping AIS ingestion")
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("AIS ingester starting")

        while self._running:
            try:
                await self._connect_and_consume()
            except Exception as exc:
                logger.error("AIS stream error, reconnecting in 5s: %s", exc)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the ingestion loop."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        # Flush remaining buffer
        if self._buffer:
            await self._flush_buffer()
        logger.info("AIS ingester stopped")

    async def _connect_and_consume(self) -> None:
        """Connect to AISStream WebSocket and process messages."""
        url = "wss://stream.aisstream.io/v0/stream"
        subscribe_msg = json.dumps({
            "APIKey": settings.ais_stream_api_key,
            "BoundingBoxes": [[[-90, -180], [90, 180]]],  # Global
            "FilterMessageTypes": ["PositionReport"],
        })

        async with websockets.connect(
            url, ping_interval=20, open_timeout=30, close_timeout=10,
        ) as ws:
            await ws.send(subscribe_msg)
            logger.info("Connected to AISStream WebSocket")

            async for raw_msg in ws:
                if not self._running:
                    break
                try:
                    msg = json.loads(raw_msg)
                    position = self._parse_position(msg)
                    if position:
                        await self._process_position(position)
                except Exception as exc:
                    logger.debug("Failed to parse AIS message: %s", exc)

    def _parse_position(self, msg: dict) -> dict | None:
        """Extract position data from AISStream message."""
        meta = msg.get("MetaData", {})
        pos = msg.get("Message", {}).get("PositionReport", {})
        if not pos:
            return None

        mmsi = meta.get("MMSI")
        if not mmsi:
            return None

        lat = pos.get("Latitude")
        lon = pos.get("Longitude")
        if lat is None or lon is None:
            return None
        if lat == 0 and lon == 0:
            return None  # Null island

        return {
            "mmsi": str(mmsi),
            "lat": lat,
            "lon": lon,
            "sog": pos.get("Sog"),
            "cog": pos.get("Cog"),
            "heading": pos.get("TrueHeading"),
            "ship_name": meta.get("ShipName", "").strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _process_position(self, position: dict) -> None:
        """Write position to Redis Geo Set and buffer for PostGIS."""
        r = await get_redis()

        # Update Redis Geo Set for spatial queries
        await r.geoadd(
            "vessels:positions",
            (position["lon"], position["lat"], position["mmsi"]),
        )

        # Store latest vessel info as hash
        await r.hset(
            f"vessel:{position['mmsi']}",
            mapping={
                "lat": str(position["lat"]),
                "lon": str(position["lon"]),
                "sog": str(position.get("sog", "")),
                "cog": str(position.get("cog", "")),
                "heading": str(position.get("heading", "")),
                "ship_name": position.get("ship_name", ""),
                "updated_at": position["timestamp"],
            },
        )

        # Publish to Redis Pub/Sub for WebSocket clients
        await r.publish("vessels:updates", json.dumps(position))

        # Buffer for PostGIS batch insert
        self._buffer.append(position)

    async def _flush_loop(self) -> None:
        """Periodically flush buffer to PostGIS."""
        while self._running:
            await asyncio.sleep(settings.ais_batch_flush_seconds)
            if self._buffer:
                await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush buffered positions to PostGIS."""
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer.clear()

        try:
            from geoalchemy2.shape import from_shape
            from shapely.geometry import Point

            from okeanus.db.postgres import async_session_factory
            from okeanus.schema.base import Observation

            async with async_session_factory() as session:
                observations = []
                for pos in batch:
                    obs = Observation(
                        obs_type="vessel",
                        timestamp=datetime.fromisoformat(pos["timestamp"]),
                        geometry=from_shape(Point(pos["lon"], pos["lat"]), srid=4326),
                        source_id=f"ais-{pos['mmsi']}-{pos['timestamp']}",
                        source_name="AISStream-live",
                        mmsi=int(pos["mmsi"]),
                        payload={
                            "sog": pos.get("sog"),
                            "cog": pos.get("cog"),
                            "heading": pos.get("heading"),
                            "ship_name": pos.get("ship_name"),
                        },
                    )
                    observations.append(obs)
                session.add_all(observations)
                await session.commit()
            logger.info("Flushed %d AIS positions to PostGIS", len(batch))
        except Exception as exc:
            logger.error("Failed to flush AIS buffer to PostGIS: %s", exc)
