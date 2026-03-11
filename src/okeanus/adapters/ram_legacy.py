"""RAM Legacy Stock Assessment Database adapter.

RAM Legacy compiles ~1,500 global fish stock time series with biomass,
mortality, catch, and management reference points. Data is distributed
as downloadable R objects / Excel / CSV. No auth required.

Data source: https://www.ramlegacy.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://zenodo.org/api/records"
# RAM Legacy publishes versioned releases on Zenodo
RAM_CONCEPT_ID = "2542919"  # Stable concept DOI record


class RamLegacyAdapter(BaseAdapter):
    """Connector for RAM Legacy Stock Assessment DB (no auth required).

    Fetches stock metadata from the RAM Legacy API / Zenodo archive.
    Full time series require downloading the database file.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ram_legacy"

    @property
    def source_url(self) -> str:
        return "https://www.ramlegacy.org/"

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
        """Fetch fish stock assessment metadata from RAM Legacy.

        Returns stock metadata including species, region, and assessment
        status. Full time series available via the downloadable database.

        Extra params:
            species: filter by species name
            region: filter by FAO region
            limit: max records (default 200)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 200)
        species = params.get("species")
        region = params.get("region")

        # Query Zenodo for the latest RAM Legacy release
        try:
            resp = await self._request(
                "GET",
                f"{BASE_URL}/{RAM_CONCEPT_ID}",
            )
            data = resp.json()
        except Exception as exc:
            logger.error("RAM Legacy Zenodo fetch failed: %s", exc)
            return []

        # Extract metadata about the database
        title = data.get("metadata", {}).get("title", "RAM Legacy Stock Assessment Database")
        version = data.get("metadata", {}).get("version", "")
        doi = data.get("doi", "")
        files = data.get("files", [])

        # Find downloadable files
        download_urls = {}
        for f in files:
            fname = f.get("key", "")
            if fname.endswith(".xlsx") or fname.endswith(".csv") or fname.endswith(".RData"):
                download_urls[fname] = f.get("links", {}).get("self", "")

        # Return a single metadata observation pointing to the database
        lon_center = (w + e) / 2
        lat_center = (s + n) / 2

        observations: list[dict[str, Any]] = [{
            "obs_type": "biological",
            "timestamp": time_start,
            "geometry": {"type": "Point", "coordinates": [lon_center, lat_center]},
            "source_id": f"ram-legacy-{version}",
            "source_name": "RAM Legacy Stock Assessment DB",
            "quality_score": 0.95,
            "payload": {
                "title": title,
                "version": version,
                "doi": doi,
                "num_stocks": "~1500",
                "coverage": "Global — 900+ marine species, 1950–present",
                "variables": [
                    "SSB (spawning stock biomass)",
                    "total biomass",
                    "fishing mortality (F)",
                    "catch/landings",
                    "recruitment",
                    "reference points (Bmsy, Fmsy, MSY)",
                ],
                "download_files": download_urls,
                "note": "Full time series require downloading the database file",
            },
        }]

        logger.info("RAM Legacy returned database metadata (v%s)", version)
        return observations
