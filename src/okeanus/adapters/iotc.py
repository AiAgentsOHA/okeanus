"""IOTC (Indian Ocean Tuna Commission) adapter.

IOTC manages tuna and tuna-like species in the Indian Ocean.
Publishes catch-effort data, size-frequency data, and stock assessments.

Data accessed via bulk CSV downloads from the IOTC data browser.
No auth required for public data.

Data source: https://iotc.org/
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# IOTC data download endpoints
NOMINAL_CATCH_URL = "https://iotc.org/sites/default/files/documents/2026/01/HISTORICAL_CATCH_ESTIMATES_0.csv"


class IotcAdapter(BaseAdapter):
    """Connector for IOTC Indian Ocean tuna catch data (no auth required).

    Returns nominal catch data by species, fleet, gear, and IOTC area.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "iotc"

    @property
    def source_url(self) -> str:
        return "https://iotc.org/"

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
        """Fetch IOTC tuna catch data.

        Extra params:
            species: species code (e.g. 'YFT', 'SKJ', 'BET')
            fleet: reporting fleet/country
            limit: max records (default 500)
        """
        limit = params.get("limit", 500)
        species_filter = params.get("species")
        fleet_filter = params.get("fleet")

        try:
            resp = await self._request("GET", NOMINAL_CATCH_URL)
            text = resp.text
        except Exception as exc:
            logger.error("IOTC data fetch failed: %s", exc)
            return []

        reader = csv.DictReader(io.StringIO(text))
        observations: list[dict[str, Any]] = []

        for row in reader:
            if len(observations) >= limit:
                break

            try:
                year = int(row.get("YEAR", row.get("Year", "0")))
            except (ValueError, TypeError):
                continue

            # IOTC data lags 2-3 years; widen range if needed
            min_year = time_start.year
            max_year = time_end.year
            if max_year - min_year < 5:
                min_year = max_year - 5
            if year < min_year or year > max_year:
                continue

            species = row.get("SPECIES_CODE", row.get("Species", row.get("SPECIES", "")))
            if species_filter and species != species_filter:
                continue

            fleet = row.get("ENTITY_CODE", row.get("Fleet", row.get("FLEET", "")))
            if fleet_filter and fleet != fleet_filter:
                continue

            catch = row.get("CATCH_MT", row.get("Catch", row.get("CATCH", "0")))
            try:
                catch_val = float(catch)
            except (ValueError, TypeError):
                catch_val = 0.0

            gear = row.get("GEAR_CODE", row.get("Gear", row.get("GEAR", "")))

            # IOTC area is Indian Ocean — approximate centroid
            area = row.get("ASSIGNED_AREA", row.get("Area", row.get("AREA", "")))
            lon, lat = _iotc_area_centroid(area)

            observations.append({
                "obs_type": "biological",
                "timestamp": datetime(year, 1, 1),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"iotc-{species}-{fleet}-{area}-{year}",
                "source_name": "IOTC",
                "quality_score": 0.9,
                "payload": {
                    "species_code": species,
                    "fleet": fleet,
                    "gear_type": gear,
                    "area": area,
                    "year": year,
                    "catch_tonnes": catch_val,
                    "data_type": "nominal_catch",
                },
            })

        logger.info("IOTC returned %d catch records", len(observations))
        return observations


def _iotc_area_centroid(area: str) -> tuple[float, float]:
    """Approximate centroid for IOTC areas."""
    # IOTC covers Indian Ocean roughly 20E-150E, 30N-60S
    return (70.0, -10.0)  # Central Indian Ocean
