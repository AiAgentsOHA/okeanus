"""AISStream.io adapter — real-time global AIS vessel positions.

WebSocket streaming API for vessel positions, identity, port calls.
AISStream provides only a WebSocket API (no REST endpoints).

API docs: https://aisstream.io/documentation
Note: Requires a free API key from https://aisstream.io/
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

WS_URL = "wss://stream.aisstream.io/v0/stream"


class AisStreamAdapter(BaseAdapter):
    """Connector for AISStream WebSocket API (free API key required).

    Streams real-time AIS data via WebSocket for a limited collection
    window, then returns accumulated vessel positions.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_key = api_key or os.environ.get("AISSTREAM_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "aisstream"

    @property
    def source_url(self) -> str:
        return WS_URL

    @property
    def update_frequency(self) -> str:
        return "real-time"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Stream AIS positions within bbox via WebSocket.

        Connects to AISStream WebSocket, subscribes to a bounding box,
        and collects messages for up to ``collect_seconds`` (default 15).

        Extra params:
            collect_seconds: how long to listen (default 15, max 60)
            mmsi: list of MMSI numbers to filter
            limit: max records to collect (default 100)
        """
        if not self._api_key:
            logger.warning("AISStream adapter requires api_key (free at aisstream.io)")
            return []

        try:
            import websockets  # noqa: F811
        except ImportError:
            logger.error("websockets package required: pip install websockets")
            return []

        collect_seconds = min(params.get("collect_seconds", 15), 60)
        mmsi_filter = params.get("mmsi", [])
        limit = params.get("limit", 100)

        w, s, e, n = bbox
        # AISStream BoundingBoxes: [[lat_min, lon_min], [lat_max, lon_max]]
        subscription = {
            "APIKey": self._api_key,
            "BoundingBoxes": [[[s, w], [n, e]]],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
        }
        if mmsi_filter:
            if isinstance(mmsi_filter, (list, tuple)):
                subscription["FiltersShipMMSI"] = [str(m) for m in mmsi_filter]
            else:
                subscription["FiltersShipMMSI"] = [str(mmsi_filter)]

        observations: list[dict[str, Any]] = []
        seen_mmsis: set[int] = set()

        try:
            async with websockets.connect(WS_URL) as ws:
                await ws.send(json.dumps(subscription))
                logger.info(
                    "AISStream: subscribed to bbox [%.1f,%.1f,%.1f,%.1f] for %ds",
                    w, s, e, n, collect_seconds,
                )

                deadline = asyncio.get_event_loop().time() + collect_seconds

                while len(observations) < limit:
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break

                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        break

                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    obs = self._parse_message(msg, seen_mmsis)
                    if obs:
                        observations.append(obs)

        except Exception as exc:
            logger.error("AISStream WebSocket failed: %s", exc)

        logger.info("AISStream returned %d vessel positions", len(observations))
        return observations

    def _parse_message(
        self,
        msg: dict[str, Any],
        seen_mmsis: set[int],
    ) -> dict[str, Any] | None:
        """Parse a single AISStream WebSocket message into an observation."""
        msg_type = msg.get("MessageType", "")
        metadata = msg.get("MetaData", {})
        message_body = msg.get("Message", {})

        if msg_type == "PositionReport":
            pos = message_body.get("PositionReport", {})
            lat = pos.get("Latitude")
            lon = pos.get("Longitude")
            mmsi_val = pos.get("UserID") or metadata.get("MMSI")

            if lat is None or lon is None:
                return None

            # Deduplicate by MMSI (keep first position per vessel)
            if mmsi_val and mmsi_val in seen_mmsis:
                return None
            if mmsi_val:
                seen_mmsis.add(mmsi_val)

            ts_str = metadata.get("time_utc", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now(timezone.utc)

            return {
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ais-{mmsi_val}-{ts.isoformat()}",
                "source_name": "AISStream",
                "mmsi": int(mmsi_val) if mmsi_val else None,
                "quality_score": 0.95,
                "payload": {
                    "vessel_name": metadata.get("ShipName", ""),
                    "speed_knots": pos.get("Sog"),
                    "heading_deg": pos.get("TrueHeading"),
                    "course_deg": pos.get("Cog"),
                    "nav_status": pos.get("NavigationalStatus"),
                    "rate_of_turn": pos.get("RateOfTurn"),
                },
            }

        elif msg_type == "ShipStaticData":
            static = message_body.get("ShipStaticData", {})
            mmsi_val = static.get("UserID") or metadata.get("MMSI")
            lat = metadata.get("latitude")
            lon = metadata.get("longitude")

            if lat is None or lon is None:
                return None

            if mmsi_val and mmsi_val in seen_mmsis:
                return None
            if mmsi_val:
                seen_mmsis.add(mmsi_val)

            ts_str = metadata.get("time_utc", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now(timezone.utc)

            return {
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ais-{mmsi_val}-{ts.isoformat()}",
                "source_name": "AISStream",
                "mmsi": int(mmsi_val) if mmsi_val else None,
                "quality_score": 0.95,
                "payload": {
                    "vessel_name": static.get("Name", metadata.get("ShipName", "")),
                    "vessel_type": static.get("Type", ""),
                    "imo": static.get("ImoNumber"),
                    "callsign": static.get("CallSign", ""),
                    "destination": static.get("Destination", ""),
                    "flag": metadata.get("country", ""),
                    "draught_m": static.get("MaximumStaticDraught"),
                },
            }

        return None
