"""IRENA (International Renewable Energy Agency) offshore wind adapter.

IRENA publishes renewable energy capacity statistics including
offshore wind installations by country, capacity, and year.

Data accessed via IRENA's PxWeb metadata API. No auth required.
Note: PxWeb POST (data query) is disabled on this instance. We use
the GET metadata endpoint to return the catalogue of countries and
years with renewable energy statistics available.

Data source: https://www.irena.org/Statistics
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# IRENA PxWeb metadata endpoint (GET only — POST disabled on this instance)
FOLDER_URL = "https://pxweb.irena.org/api/v1/en/IRENASTAT/Power%20Capacity%20and%20Generation/"

# Offshore wind countries with approximate coastal centroids (lon, lat)
_CENTROIDS: dict[str, tuple[float, float]] = {
    "CHN": (121.0, 31.0), "GBR": (-1.0, 53.0), "DEU": (8.0, 54.0),
    "NLD": (4.0, 52.5), "DNK": (10.0, 56.0), "BEL": (3.0, 51.3),
    "USA": (-73.0, 40.0), "TWN": (120.0, 24.0), "VNM": (108.0, 16.0),
    "JPN": (139.0, 35.0), "KOR": (127.0, 36.0), "FRA": (-2.0, 47.0),
    "NOR": (5.0, 60.0), "IND": (80.0, 15.0), "ITA": (12.0, 42.0),
    "ESP": (-4.0, 43.0), "POL": (18.0, 55.0), "IRL": (-10.0, 53.0),
    "PRT": (-9.0, 39.0), "GRC": (24.0, 38.0), "SWE": (18.0, 59.0),
    "FIN": (24.0, 62.0), "BRA": (-40.0, -10.0), "AUS": (150.0, -34.0),
}


class IrenaOffshoreAdapter(BaseAdapter):
    """Connector for IRENA offshore wind energy statistics (no auth required).

    Uses PxWeb GET metadata API to discover the current table and
    returns country-level offshore wind statistics records.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "irena_offshore"

    @property
    def source_url(self) -> str:
        return "https://www.irena.org/Statistics"

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
        """Fetch IRENA offshore wind statistics metadata.

        Extra params:
            country: ISO3 country code filter
            limit: max records (default 500)
        """
        limit = params.get("limit", 500)
        country_filter = params.get("country")
        w, s, e, n = bbox

        # Step 1: Discover current table filename from folder listing
        try:
            resp = await self._request("GET", FOLDER_URL)
            tables = resp.json()
        except Exception as exc:
            logger.error("IRENA folder listing failed: %s", exc)
            return []

        # Find the Country_ELECSTAT table
        table_id = None
        for tbl in tables:
            tid = tbl.get("id", "")
            if "Country_ELECSTAT" in tid:
                table_id = tid
                break

        if not table_id:
            logger.error("IRENA: Could not find Country_ELECSTAT table")
            return []

        # Step 2: Get table metadata
        table_url = f"{FOLDER_URL}{table_id}"
        try:
            resp = await self._request("GET", table_url)
            meta = resp.json()
        except Exception as exc:
            logger.error("IRENA table metadata failed: %s", exc)
            return []

        # Parse variables
        variables = {v["code"]: v for v in meta.get("variables", [])}

        country_var = variables.get("Country/area", {})
        country_codes = country_var.get("values", [])
        country_names = country_var.get("valueTexts", [])

        year_var = variables.get("Year", {})
        year_texts = year_var.get("valueTexts", [])

        tech_var = variables.get("Technology", {})
        tech_texts = tech_var.get("valueTexts", [])
        offshore_idx = None
        marine_idx = None
        for i, t in enumerate(tech_texts):
            if "Offshore wind" in t:
                offshore_idx = i
            if "Marine energy" in t:
                marine_idx = i

        # Filter years to requested range
        valid_years = [
            int(y) for y in year_texts
            if y.isdigit() and time_start.year <= int(y) <= time_end.year
        ]
        if not valid_years:
            valid_years = [int(y) for y in year_texts if y.isdigit()][-5:]

        observations: list[dict[str, Any]] = []

        for i, code in enumerate(country_codes):
            if len(observations) >= limit:
                break

            if country_filter and code != country_filter:
                continue

            # Get centroid; skip if not in bbox
            lon, lat = _CENTROIDS.get(code, (0.0, 0.0))
            if lon == 0.0 and lat == 0.0:
                continue  # Only emit countries with known offshore wind
            if not (w <= lon <= e and s <= lat <= n):
                continue

            name = country_names[i] if i < len(country_names) else code

            for year in valid_years:
                if len(observations) >= limit:
                    break

                observations.append({
                    "obs_type": "economic",
                    "timestamp": datetime(year, 1, 1),
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"irena-{code}-offshore-{year}",
                    "source_name": "IRENA",
                    "quality_score": 0.85,
                    "payload": {
                        "country_code": code,
                        "country_name": name,
                        "technology": "Offshore wind energy",
                        "technology_index": offshore_idx,
                        "marine_energy_index": marine_idx,
                        "year": year,
                        "data_table": table_id,
                        "available_years": year_texts,
                        "note": "Capacity values require PxWeb POST (disabled); metadata only",
                    },
                })

        logger.info("IRENA returned %d offshore wind records", len(observations))
        return observations
