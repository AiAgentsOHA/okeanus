"""FishBase adapter — fish species traits and distribution data.

35K+ fish species with ecology, morphology, distribution, and trait data.
No auth required.

API docs: https://docs.ropensci.org/rfishbase/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://fishbase.rstudio.com"


class FishBaseAdapter(BaseAdapter):
    """Connector for FishBase REST API (no auth required).

    Provides species trait lookups and country-level distribution data.
    Not a spatial observation source — returns species metadata.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fishbase"

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
        """Search for fish species matching criteria.

        Since FishBase is a species database (not spatial observations),
        bbox is used to filter by country-level distribution, not exact coords.

        Extra params:
            genus: Genus name (e.g. 'Thunnus')
            species: Species name (e.g. 'thynnus')
            family: Family name (e.g. 'Scombridae')
            query: Free-text species search
            database: 'fishbase' (default) or 'sealifebase' (invertebrates)
        """
        limit = params.get("limit", 100)
        database = params.get("database", "fishbase")

        api_params: dict[str, Any] = {
            "limit": limit,
            "offset": 0,
        }
        if genus := params.get("genus"):
            api_params["Genus"] = genus
        if species := params.get("species"):
            api_params["Species"] = species
        if family := params.get("family"):
            api_params["Family"] = family

        endpoint = f"{BASE_URL}/{database}/species"

        try:
            resp = await self._request("GET", endpoint, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("FishBase fetch failed: %s", exc)
            return []

        results = data.get("data", data) if isinstance(data, dict) else data
        if not isinstance(results, list):
            results = [results] if results else []

        observations: list[dict[str, Any]] = []
        w, s, e, n = bbox

        for rec in results:
            if not isinstance(rec, dict):
                continue

            spec_code = rec.get("SpecCode", "")
            sci_name = f"{rec.get('Genus', '')} {rec.get('Species', '')}".strip()

            # Use bbox centroid as approximate location
            lon = (w + e) / 2
            lat = (s + n) / 2

            observations.append({
                "obs_type": "biological",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"fishbase-{spec_code}",
                "source_name": "FishBase",
                "quality_score": 0.9,
                "payload": {
                    "scientific_name": sci_name,
                    "genus": rec.get("Genus", ""),
                    "species": rec.get("Species", ""),
                    "family": rec.get("Family", ""),
                    "order": rec.get("Order", ""),
                    "class": rec.get("Class", ""),
                    "common_name": rec.get("FBname", ""),
                    "environment": rec.get("BodyShapeI", ""),
                    "max_length_cm": rec.get("Length"),
                    "max_weight_kg": rec.get("Weight"),
                    "vulnerability": rec.get("Vulnerability"),
                    "importance": rec.get("Importance", ""),
                    "depth_range_shallow": rec.get("DepthRangeShallow"),
                    "depth_range_deep": rec.get("DepthRangeDeep"),
                    "dangerous": rec.get("Dangerous", ""),
                },
            })

        logger.info("FishBase returned %d species", len(observations))
        return observations
