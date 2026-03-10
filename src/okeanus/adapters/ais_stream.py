"""AISStream.io adapter — real-time global AIS vessel positions.

WebSocket streaming + REST API for vessel positions, identity, port calls.

API docs: https://aisstream.io/documentation
Note: Requires a free API key from https://aisstream.io/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.aisstream.io/v0"


class AisStreamAdapter(BaseAdapter):
    """Connector for AISStream REST API (free API key required)."""

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        return "aisstream"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """Fetch recent AIS positions within bbox.

        Uses the AISStream REST search endpoint (not WebSocket).
        For real-time streaming, use the WebSocket API directly.
        """
        if not self._api_key:
            logger.warning("AISStream adapter requires api_key (free at aisstream.io)")
            return []

        w, s, e, n = bbox
        headers = {"Authorization": f"Bearer {self._api_key}"}

        body: dict[str, Any] = {
            "area": {
                "type": "Polygon",
                "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
            },
            "timeRange": {
                "start": time_start.isoformat(),
                "end": time_end.isoformat(),
            },
        }
        if mmsi := params.get("mmsi"):
            body["mmsi"] = mmsi

        try:
            resp = await self._request(
                "POST", f"{BASE_URL}/vessels/search",
                json=body, headers=headers,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("AISStream fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", [])
        observations: list[dict[str, Any]] = []

        for rec in records:
            pos = rec.get("position", rec.get("lastPosition", {}))
            lon = pos.get("longitude", pos.get("lon"))
            lat = pos.get("latitude", pos.get("lat"))
            if lon is None or lat is None:
                continue

            ts_str = pos.get("timestamp") or rec.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now()

            mmsi_val = rec.get("mmsi")

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ais-{mmsi_val}-{ts.isoformat()}",
                "source_name": "AISStream",
                "mmsi": int(mmsi_val) if mmsi_val else None,
                "quality_score": 0.95,
                "payload": {
                    "vessel_name": rec.get("name", rec.get("shipName", "")),
                    "vessel_type": rec.get("shipType", ""),
                    "speed_knots": rec.get("speed", pos.get("speed")),
                    "heading_deg": rec.get("heading", pos.get("heading")),
                    "course_deg": rec.get("course", pos.get("course")),
                    "flag": rec.get("flag", ""),
                    "imo": rec.get("imo"),
                    "callsign": rec.get("callsign", ""),
                    "destination": rec.get("destination", ""),
                    "draught_m": rec.get("draught"),
                },
            })

        logger.info("AISStream returned %d vessel positions", len(observations))
        return observations
