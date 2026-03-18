"""Happywhale adapter — individual whale encounters via GBIF.

Happywhale (happywhale.com) publishes cetacean photo-ID encounters to GBIF.
This adapter queries GBIF's occurrence API filtered to the Happywhale
publishing organisation, returning individual whale sightings with
species, encounter date, and dataset metadata. No auth required.

Source: https://happywhale.com / https://www.gbif.org/publisher/67b2263f-6990-4d9d-b32b-20aa72ef4fbc
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

GBIF_API = "https://api.gbif.org/v1/occurrence/search"
HAPPYWHALE_ORG = "67b2263f-6990-4d9d-b32b-20aa72ef4fbc"


class HappywhaleAdapter(BaseAdapter):
    """Connector for Happywhale cetacean encounters via GBIF (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=3.0, timeout=45.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "happywhale"

    @property
    def source_url(self) -> str:
        return "https://happywhale.com"

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
        """Fetch whale encounters from Happywhale via GBIF.

        Extra params:
            species: Filter by species name (e.g. 'Megaptera novaeangliae')
            limit: Max records (default 200)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 200)
        species = params.get("species", "")

        geometry = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"

        api_params: dict[str, Any] = {
            "publishingOrg": HAPPYWHALE_ORG,
            "geometry": geometry,
            "eventDate": (
                f"{time_start.strftime('%Y-%m-%d')},"
                f"{time_end.strftime('%Y-%m-%d')}"
            ),
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": min(limit, 300),
        }
        if species:
            api_params["scientificName"] = species

        try:
            resp = await self._request("GET", GBIF_API, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Happywhale/GBIF fetch failed: %s", exc)
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
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(
                        str(date_str).replace("Z", "+00:00")
                    )
                else:
                    ts = datetime.fromisoformat(
                        str(date_str)[:10] + "T00:00:00+00:00"
                    )
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"happywhale-{rec.get('gbifID', rec.get('key', ''))}",
                "source_name": "Happywhale",
                "quality_score": 0.9,
                "payload": {
                    "scientific_name": rec.get("scientificName", ""),
                    "species": rec.get("species", ""),
                    "order": rec.get("order", ""),
                    "family": rec.get("family", ""),
                    "catalog_number": rec.get("catalogNumber", ""),
                    "occurrence_id": rec.get("occurrenceID", ""),
                    "basis_of_record": rec.get("basisOfRecord", ""),
                    "dataset_name": rec.get("datasetName", ""),
                    "country": rec.get("countryCode", ""),
                    "individual_count": rec.get("individualCount"),
                    "recorded_by": rec.get("recordedBy", ""),
                },
            })

        logger.info("Happywhale returned %d encounters", len(observations))
        return observations
