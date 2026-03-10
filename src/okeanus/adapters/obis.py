"""OBIS (Ocean Biodiversity Information System) adapter.

130M+ marine species occurrence records via the OBIS REST API.
Returns biological observations with WoRMS AphiaID linking.

API docs: https://api.obis.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.obis.org/v3"


class ObisAdapter(BaseAdapter):
    """Connector for the OBIS occurrence REST API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "obis"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch species occurrence records within bbox and time range."""
        w, s, e, n = bbox
        geometry = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
        size = params.get("size", 500)

        api_params: dict[str, Any] = {
            "geometry": geometry,
            "startdate": time_start.strftime("%Y-%m-%d"),
            "enddate": time_end.strftime("%Y-%m-%d"),
            "size": size,
        }
        if taxon := params.get("taxon"):
            api_params["scientificname"] = taxon

        try:
            resp = await self._request("GET", f"{BASE_URL}/occurrence", params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("OBIS fetch failed: %s", exc)
            return []

        results = data.get("results", [])
        observations: list[dict[str, Any]] = []

        for rec in results:
            lon = rec.get("decimalLongitude")
            lat = rec.get("decimalLatitude")
            date_str = rec.get("eventDate") or rec.get("date_mid")
            if lon is None or lat is None or date_str is None:
                continue

            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            aphia = rec.get("aphiaID") or rec.get("speciesid")

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"obis-{rec.get('id', rec.get('occurrenceID', ''))}",
                "source_name": "OBIS",
                "aphia_id": int(aphia) if aphia else None,
                "quality_score": None,
                "payload": {
                    "scientific_name": rec.get("scientificName", ""),
                    "phylum": rec.get("phylum", ""),
                    "class": rec.get("class", ""),
                    "order": rec.get("order", ""),
                    "family": rec.get("family", ""),
                    "genus": rec.get("genus", ""),
                    "species": rec.get("species", ""),
                    "dataset_name": rec.get("dataset_id", ""),
                    "basis_of_record": rec.get("basisOfRecord", ""),
                    "depth_m": rec.get("depth"),
                    "individual_count": rec.get("individualCount"),
                },
            })

        logger.info("OBIS returned %d occurrences", len(observations))
        return observations
