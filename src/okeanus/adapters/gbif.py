"""GBIF (Global Biodiversity Information Facility) adapter.

Marine species occurrences from the GBIF occurrence search API.
No auth required for basic searches.

API docs: https://www.gbif.org/developer/occurrence
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.gbif.org/v1"


class GbifAdapter(BaseAdapter):
    """Connector for GBIF occurrence search (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=3.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "gbif"

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
        """Fetch marine species occurrences within bbox and time range."""
        w, s, e, n = bbox
        limit = params.get("limit", 300)

        geometry = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"

        api_params: dict[str, Any] = {
            "geometry": geometry,
            "eventDate": f"{time_start.strftime('%Y-%m-%d')},{time_end.strftime('%Y-%m-%d')}",
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": limit,
        }
        # Filter to marine taxa if requested
        if taxon_key := params.get("taxon_key"):
            api_params["taxonKey"] = taxon_key

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/occurrence/search", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("GBIF fetch failed: %s", exc)
            return []

        results = data.get("results", [])
        observations: list[dict[str, Any]] = []

        for rec in results:
            lon = rec.get("decimalLongitude")
            lat = rec.get("decimalLatitude")
            if lon is None or lat is None:
                continue

            date_str = rec.get("eventDate", "")
            try:
                if "T" in date_str:
                    ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else:
                    ts = datetime.fromisoformat(date_str + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"gbif-{rec.get('gbifID', rec.get('key', ''))}",
                "source_name": "GBIF",
                "quality_score": None,
                "payload": {
                    "scientific_name": rec.get("scientificName", ""),
                    "species": rec.get("species", ""),
                    "kingdom": rec.get("kingdom", ""),
                    "phylum": rec.get("phylum", ""),
                    "class": rec.get("class", ""),
                    "order": rec.get("order", ""),
                    "family": rec.get("family", ""),
                    "basis_of_record": rec.get("basisOfRecord", ""),
                    "dataset_name": rec.get("datasetName", ""),
                    "institution": rec.get("institutionCode", ""),
                    "country": rec.get("countryCode", ""),
                    "depth_m": rec.get("depth"),
                    "individual_count": rec.get("individualCount"),
                },
            })

        logger.info("GBIF returned %d occurrences", len(observations))
        return observations
