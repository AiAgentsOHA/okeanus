"""Smithsonian Global Volcanism Program adapter — submarine volcanoes.

The GVP maintains the authoritative database of ~3,000 active volcanoes
including submarine and island-arc volcanoes. REST/download access via
the Holocene Volcano List. No auth required.

Data source: https://volcano.si.edu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://volcano.si.edu/api/v1"
SEARCH_URL = "https://volcano.si.edu/database/search_eruption_results.cfm"


class SmithsonianVolcanoesAdapter(BaseAdapter):
    """Connector for Smithsonian GVP volcano database (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "smithsonian_volcanoes"

    @property
    def source_url(self) -> str:
        return "https://volcano.si.edu/"

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch volcano data within bbox.

        Extra params:
            submarine_only: if True, only submarine volcanoes (default True)
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        submarine_only = params.get("submarine_only", True)

        # Use the GVP search endpoint for volcano list
        api_params: dict[str, Any] = {
            "lat_min": s,
            "lat_max": n,
            "lon_min": w,
            "lon_max": e,
            "format": "json",
        }

        if submarine_only:
            api_params["type"] = "Submarine"

        try:
            resp = await self._request("GET", f"{BASE_URL}/volcanoes", params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Smithsonian GVP fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("volcanoes", data.get("results", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("longitude", rec.get("Longitude"))
            lat = rec.get("latitude", rec.get("Latitude"))
            if lon is None or lat is None:
                continue

            try:
                lon, lat = float(lon), float(lat)
            except (ValueError, TypeError):
                continue

            last_eruption = rec.get("last_eruption_year", rec.get("LastEruptionYear"))
            try:
                ts = datetime(int(last_eruption), 1, 1) if last_eruption else time_start
            except (ValueError, TypeError):
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"gvp-{rec.get('volcano_number', rec.get('VolcanoNumber', ''))}",
                "source_name": "Smithsonian GVP",
                "quality_score": 0.95,
                "payload": {
                    "volcano_name": rec.get("volcano_name", rec.get("VolcanoName", "")),
                    "volcano_number": rec.get("volcano_number", rec.get("VolcanoNumber")),
                    "primary_type": rec.get("primary_volcano_type", rec.get("Type", "")),
                    "country": rec.get("country", rec.get("Country", "")),
                    "region": rec.get("region", rec.get("Region", "")),
                    "summit_elevation_m": rec.get("elevation_m", rec.get("Elevation")),
                    "last_eruption_year": last_eruption,
                    "tectonic_setting": rec.get("tectonic_setting", ""),
                    "dominant_rock_type": rec.get("dominant_rock_type", ""),
                },
            })

        logger.info("Smithsonian GVP returned %d volcanoes", len(observations))
        return observations
