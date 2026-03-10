"""SeaLifeBase adapter — marine invertebrate species traits and data.

Sister database to FishBase covering marine invertebrates including
molluscs, crustaceans, echinoderms, and other non-fish marine species.
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


class SeaLifeBaseAdapter(BaseAdapter):
    """Connector for SeaLifeBase REST API (no auth required).

    Uses the same API infrastructure as FishBase but queries the
    SeaLifeBase database path for invertebrate records.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "sealifebase"

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
        """Search for marine invertebrate species matching criteria.

        Extra params:
            genus: Genus name (e.g. 'Octopus')
            species: Species name (e.g. 'vulgaris')
            family: Family name (e.g. 'Octopodidae')
            order: Order name (e.g. 'Octopoda')
            limit: Max results (default 100)
        """
        limit = params.get("limit", 100)

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
        if order := params.get("order"):
            api_params["Order"] = order

        endpoint = f"{BASE_URL}/sealifebase/species"

        try:
            resp = await self._request("GET", endpoint, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("SeaLifeBase fetch failed: %s", exc)
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

            lon = (w + e) / 2
            lat = (s + n) / 2

            observations.append({
                "obs_type": "biological",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"sealifebase-{spec_code}",
                "source_name": "SeaLifeBase",
                "quality_score": 0.9,
                "payload": {
                    "scientific_name": sci_name,
                    "genus": rec.get("Genus", ""),
                    "species": rec.get("Species", ""),
                    "family": rec.get("Family", ""),
                    "order": rec.get("Order", ""),
                    "class": rec.get("Class", ""),
                    "common_name": rec.get("FBname", ""),
                    "max_length_cm": rec.get("Length"),
                    "max_weight_kg": rec.get("Weight"),
                    "depth_range_shallow": rec.get("DepthRangeShallow"),
                    "depth_range_deep": rec.get("DepthRangeDeep"),
                    "importance": rec.get("Importance", ""),
                    "dangerous": rec.get("Dangerous", ""),
                },
            })

        logger.info("SeaLifeBase returned %d species", len(observations))
        return observations
