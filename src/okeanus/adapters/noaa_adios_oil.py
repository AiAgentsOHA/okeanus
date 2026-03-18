"""NOAA ADIOS Oil Library adapter — oil property records for spill response.

The ADIOS (Automated Data Inquiry for Oil Spills) oil library contains
physical and chemical properties of 1000+ oils. Data available via the
noaa-oil-data GitHub repository as individual JSON files.

Source: https://github.com/NOAA-ORR-ERD/noaa-oil-data
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# GitHub API to list oil record directories (7 prefix dirs: AD, EC, EX, GN, IM, LS, NO)
GITHUB_API = "https://api.github.com/repos/NOAA-ORR-ERD/noaa-oil-data/contents/data/oil"
RAW_BASE = "https://raw.githubusercontent.com/NOAA-ORR-ERD/noaa-oil-data/production/data/oil"


class NoaaAdiosOilAdapter(BaseAdapter):
    """Connector for NOAA ADIOS Oil Library (GitHub-hosted JSON)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, timeout=30.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_adios_oil"

    @property
    def source_url(self) -> str:
        return "https://github.com/NOAA-ORR-ERD/noaa-oil-data"

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
        """Fetch oil property records from the ADIOS library via GitHub.

        Note: Oil records are not spatially referenced — bbox is ignored.

        Extra params:
            prefix: Oil ID prefix to browse ('AD', 'EC', 'EX', 'GN', 'IM', 'LS', 'NO')
            limit: Max records (default 20, max 50 to respect GitHub rate limits)
        """
        limit = min(params.get("limit", 20), 50)
        prefix = params.get("prefix", "AD").upper()

        # List files in the prefix directory
        list_url = f"{GITHUB_API}/{prefix}"
        try:
            resp = await self._request(
                "GET", list_url,
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            files = resp.json()
        except Exception as exc:
            logger.error("NOAA ADIOS GitHub listing failed: %s", exc)
            return []

        if not isinstance(files, list):
            logger.error("NOAA ADIOS unexpected response: %s", type(files))
            return []

        # Filter to JSON files only
        json_files = [f for f in files if f.get("name", "").endswith(".json")][:limit]

        observations: list[dict[str, Any]] = []
        ts = datetime.now(timezone.utc)

        for file_info in json_files:
            fname = file_info["name"]
            oil_id = fname.replace(".json", "")
            raw_url = f"{RAW_BASE}/{prefix}/{fname}"

            try:
                resp = await self._request("GET", raw_url)
                rec = resp.json()
            except Exception:
                continue

            meta = rec.get("metadata", {})
            name = meta.get("name", "")
            product_type = meta.get("product_type", "")
            ref = meta.get("reference", {})

            observations.append({
                "obs_type": "oil_properties",
                "timestamp": ts,
                "geometry": None,
                "source_id": f"adios-{oil_id}",
                "source_name": "NOAA ADIOS Oil Library",
                "quality_score": 0.95,
                "payload": {
                    "oil_id": oil_id,
                    "name": name,
                    "product_type": product_type,
                    "api_gravity": meta.get("API"),
                    "location": meta.get("location", ""),
                    "reference": ref.get("reference", "") if isinstance(ref, dict) else str(ref),
                    "reference_year": ref.get("year", "") if isinstance(ref, dict) else "",
                },
            })

        logger.info("NOAA ADIOS returned %d oil records", len(observations))
        return observations
