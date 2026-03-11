"""IUCN Red List adapter — marine species conservation status.

Provides access to the IUCN Red List API for marine species assessments
including threat categories, population trends, and habitat information.
Requires a free API token from https://apiv3.iucnredlist.org/api/v3/token

Data source: https://www.iucnredlist.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://apiv3.iucnredlist.org/api/v3"


class IucnRedlistAdapter(BaseAdapter):
    """Connector for IUCN Red List API (free token required).

    Without a token, returns publicly available summary data.
    """

    def __init__(self, api_token: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_token = api_token

    @property
    def source_name(self) -> str:
        return "iucn_redlist"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch marine species from the IUCN Red List.

        Extra params:
            species_name: search by species name
            category: filter by threat category (e.g. 'CR', 'EN', 'VU')
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)
        species_name = params.get("species_name")
        category = params.get("category")

        token_suffix = f"?token={self._api_token}" if self._api_token else ""

        # Search for marine species
        if species_name:
            url = f"{BASE_URL}/species/{species_name}{token_suffix}"
        else:
            # Fetch marine species by region (global)
            url = f"{BASE_URL}/comp-group/getlistid/marine%20mammals{token_suffix}"

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("IUCN Red List fetch failed: %s", exc)
            return []

        results = data.get("result", [])
        if not isinstance(results, list):
            results = [results] if isinstance(results, dict) else []

        observations: list[dict[str, Any]] = []
        w, s, e, n = bbox

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            # IUCN doesn't provide exact coordinates; use bbox centroid
            lon = (w + e) / 2
            lat = (s + n) / 2

            rec_category = rec.get("category", "")
            if category and rec_category != category:
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"iucn-{rec.get('taxonid', rec.get('species_id', ''))}",
                "source_name": "IUCN Red List",
                "quality_score": 0.95,
                "payload": {
                    "scientific_name": rec.get("scientific_name", rec.get("scientificname", "")),
                    "common_name": rec.get("main_common_name", ""),
                    "category": rec_category,
                    "population_trend": rec.get("population_trend", ""),
                    "class": rec.get("class_name", ""),
                    "order": rec.get("order_name", ""),
                    "family": rec.get("family_name", ""),
                    "assessment_date": rec.get("assessment_date", ""),
                    "criteria": rec.get("criteria", ""),
                    "marine_system": rec.get("marine_system"),
                },
            })

        logger.info("IUCN Red List returned %d species", len(observations))
        return observations
