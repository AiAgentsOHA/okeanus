"""Orcasound adapter — live whale call hydrophone network.

Orcasound operates hydrophone stations in Puget Sound streaming live
audio for killer whale detection. Provides labeled whale call datasets
and real-time node status. No auth required.

Data source: https://www.orcasound.net/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.orcasound.net/api"

# Known hydrophone nodes
NODES = {
    "bush_point": {"lat": 48.0336, "lon": -122.6040, "name": "Bush Point"},
    "port_townsend": {"lat": 48.1317, "lon": -122.7603, "name": "Port Townsend"},
    "orcasound_lab": {"lat": 48.5583, "lon": -123.0500, "name": "Orcasound Lab"},
    "sunset_bay": {"lat": 48.5340, "lon": -123.0085, "name": "Sunset Bay"},
    "north_san_juan": {"lat": 48.6000, "lon": -123.1000, "name": "North San Juan Channel"},
}


class OrcasoundAdapter(BaseAdapter):
    """Connector for Orcasound hydrophone network (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "orcasound"

    @property
    def source_url(self) -> str:
        return "https://www.orcasound.net/"

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
        """Fetch hydrophone node status and recent detections.

        Extra params:
            node: specific node name (e.g. 'bush_point')
        """
        w, s, e, n = bbox
        target_node = params.get("node")

        observations: list[dict[str, Any]] = []

        # Check which nodes fall within bbox
        for node_id, node_info in NODES.items():
            if target_node and node_id != target_node:
                continue

            lat = node_info["lat"]
            lon = node_info["lon"]

            if not (w <= lon <= e and s <= lat <= n):
                continue

            # Query node status
            try:
                resp = await self._request("GET", f"{BASE_URL}/feeds")
                data = resp.json()
            except Exception as exc:
                logger.warning("Orcasound feeds fetch failed: %s", exc)
                data = {"data": []}

            feeds = data.get("data", []) if isinstance(data, dict) else data
            node_status = "unknown"

            for feed in feeds:
                if not isinstance(feed, dict):
                    continue
                attrs = feed.get("attributes", feed)
                if node_info["name"].lower() in str(attrs.get("name", "")).lower():
                    node_status = "online" if attrs.get("visible") else "offline"
                    break

            observations.append({
                "obs_type": "physical",
                "timestamp": datetime.utcnow(),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"orcasound-{node_id}",
                "source_name": "Orcasound",
                "quality_score": 0.85,
                "payload": {
                    "node_name": node_info["name"],
                    "node_id": node_id,
                    "status": node_status,
                    "species_monitored": "Orcinus orca (Southern Resident Killer Whale)",
                    "stream_type": "HLS audio",
                    "sample_rate_hz": 48000,
                },
            })

        logger.info("Orcasound returned %d nodes", len(observations))
        return observations
