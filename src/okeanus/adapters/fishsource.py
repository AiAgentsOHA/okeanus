"""FishSource adapter -- sustainable fisheries scorecard data.

FishSource (Sustainable Fisheries Partnership) provides sustainability
scores for ~2,000 fisheries covering management quality, stock health,
and environmental impacts.

NOTE: The FishSource REST API (/api/v1/) was decommissioned circa 2025.
This adapter falls back to the Sea Around Us taxa API for global fishery
species data (functional groups, commercial groups, scientific names).

Data source: https://www.fishsource.org/ (API decommissioned)
Fallback:    https://api.seaaroundus.org/api/v1/taxa/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Sea Around Us public REST API for taxa (no auth required)
SAU_TAXA_URL = "https://api.seaaroundus.org/api/v1/taxa/"

SITE_URL = "https://www.fishsource.org/"


class FishSourceAdapter(BaseAdapter):
    """Connector for fishery species / sustainability data.

    The original FishSource REST API is no longer available. This adapter
    uses the Sea Around Us taxa API as a fallback, providing fishery species
    data with functional and commercial group classifications.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fishsource"

    @property
    def source_url(self) -> str:
        return SITE_URL

    @property
    def update_frequency(self) -> str:
        return "quarterly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch fishery taxa data from Sea Around Us (fallback for dead FishSource API).

        Extra params:
            limit: max records (default 200)
        """
        limit = params.get("limit", 200)
        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        try:
            resp = await self._request(
                "GET", SAU_TAXA_URL, params={"limit": limit}
            )
            data = resp.json()
        except Exception as exc:
            logger.error("FishSource/SAU taxa fetch failed: %s", exc)
            return []

        records = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if len(observations) >= limit:
                break
            if not isinstance(rec, dict):
                continue

            taxon_key = rec.get("taxon_key", "")
            sci_name = rec.get("scientific_name", "")
            common_name = rec.get("common_name", "")

            observations.append({
                "obs_type": "biological",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                "source_id": f"fishsource-sau-{taxon_key}",
                "source_name": "FishSource / Sea Around Us",
                "quality_score": 0.8,
                "payload": {
                    "taxon_key": taxon_key,
                    "scientific_name": sci_name,
                    "common_name": common_name,
                    "functional_group": rec.get("functional_group"),
                    "commercial_group": rec.get("commercial_group"),
                    "source_note": "FishSource API decommissioned; data from Sea Around Us",
                },
            })

        logger.info("FishSource returned %d fisheries", len(observations))
        return observations
