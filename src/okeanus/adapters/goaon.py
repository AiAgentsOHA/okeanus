"""GOA-ON adapter — Global Ocean Acidification Observing Network.

GOA-ON coordinates ocean acidification observations from 1,000+ members
in 100+ countries. Provides station locations and metadata via their
public data portal. No auth required.

Data source: https://www.goa-on.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.goa-on.org/api/assets"


class GoaOnAdapter(BaseAdapter):
    """Connector for GOA-ON ocean acidification network (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "goaon"

    @property
    def source_url(self) -> str:
        return "https://www.goa-on.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch GOA-ON station locations and metadata within bbox.

        Extra params:
            platform_type: filter by platform (e.g. 'buoy', 'ship', 'mooring')
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        platform_type = params.get("platform_type")

        api_params: dict[str, Any] = {
            "min_lat": s,
            "max_lat": n,
            "min_lon": w,
            "max_lon": e,
            "format": "json",
        }

        if platform_type:
            api_params["platform_type"] = platform_type

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("GOA-ON fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("assets", data.get("stations", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("longitude", rec.get("lon"))
            lat = rec.get("latitude", rec.get("lat"))
            if lon is None or lat is None:
                continue

            try:
                lon, lat = float(lon), float(lat)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"goaon-{rec.get('id', rec.get('asset_id', ''))}",
                "source_name": "GOA-ON",
                "quality_score": 0.85,
                "payload": {
                    "station_name": rec.get("name", rec.get("station_name", "")),
                    "platform_type": rec.get("platform_type", rec.get("type", "")),
                    "variables": rec.get("variables", rec.get("parameters", [])),
                    "country": rec.get("country", ""),
                    "organization": rec.get("organization", rec.get("institution", "")),
                    "depth_m": rec.get("depth"),
                    "status": rec.get("status", ""),
                    "data_url": rec.get("data_url", ""),
                },
            })

        logger.info("GOA-ON returned %d stations", len(observations))
        return observations
