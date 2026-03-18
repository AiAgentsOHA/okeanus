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

FEEDS_URL = "https://live.orcasound.net/api/json/feeds"


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
            node: specific node slug (e.g. 'bush-point')
        """
        w, s, e, n = bbox
        target_node = params.get("node")

        # Fetch all feeds in a single request
        try:
            resp = await self._request("GET", FEEDS_URL)
            data = resp.json()
        except Exception as exc:
            logger.error("Orcasound feeds fetch failed: %s", exc)
            return []

        feeds = data.get("data", []) if isinstance(data, dict) else data
        observations: list[dict[str, Any]] = []

        for feed in feeds:
            if not isinstance(feed, dict):
                continue

            attrs = feed.get("attributes", feed)
            slug = attrs.get("slug", "")
            node_name = attrs.get("node_name", slug)

            if target_node and slug != target_node:
                continue

            # Extract coordinates from the API response
            loc = attrs.get("location_point") or {}
            lat_lng = attrs.get("lat_lng") or {}
            coords = loc.get("coordinates")  # [lon, lat]
            if coords and len(coords) >= 2:
                lon, lat = float(coords[0]), float(coords[1])
            elif lat_lng:
                lon = float(lat_lng.get("lng", 0))
                lat = float(lat_lng.get("lat", 0))
            else:
                continue

            # Filter by bbox
            if not (w <= lon <= e and s <= lat <= n):
                continue

            visible = attrs.get("visible", False)
            node_status = "online" if visible else "offline"

            observations.append({
                "obs_type": "physical",
                "timestamp": datetime.utcnow(),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"orcasound-{slug or feed.get('id', '')}",
                "source_name": "Orcasound",
                "quality_score": 0.85,
                "payload": {
                    "node_name": attrs.get("name", ""),
                    "node_id": node_name,
                    "slug": slug,
                    "status": node_status,
                    "bucket": attrs.get("bucket", ""),
                    "species_monitored": "Orcinus orca (Southern Resident Killer Whale)",
                    "stream_type": "HLS audio",
                    "sample_rate_hz": 48000,
                },
            })

        logger.info("Orcasound returned %d nodes", len(observations))
        return observations
