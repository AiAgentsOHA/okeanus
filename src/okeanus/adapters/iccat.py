"""ICCAT (International Commission for Conservation of Atlantic Tunas) adapter.

ICCAT manages tuna and tuna-like species in the Atlantic Ocean.
Publishes catch statistics, stock assessments, and vessel data.

Data accessed via bulk CSV downloads from the ICCAT statistical database.
No auth required for public statistical data.

Data source: https://www.iccat.int/
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# ICCAT statistical databases — publicly available downloads
# The bulk CSV is distributed as a zip; the filename changes with each update.
# We try the latest known URL first, then fall back to the EFFDIS effort/catch CSV.
_T1NC_ZIP_URLS = [
    "https://www.iccat.int/Data/t1nc_20260129.zip",
    "https://www.iccat.int/Data/ICCAT.zip",
]
# EFFDIS (effort + catch by 5x5 grid) — always available as plain CSV
EFFDIS_URL = "https://www.iccat.int/Data/EFFDIS_LL2000-2024.csv"


class IccatAdapter(BaseAdapter):
    """Connector for ICCAT Atlantic tuna catch statistics (no auth required).

    Returns nominal catch data by species, flag state, gear type,
    and ICCAT statistical area.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "iccat"

    @property
    def source_url(self) -> str:
        return "https://www.iccat.int/"

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
        """Fetch ICCAT tuna catch data.

        Uses the EFFDIS longline effort/catch CSV (plain CSV, always
        available) as the primary data source.  The T1NC bulk zip is
        tried first when *prefer_t1nc* is True.

        Extra params:
            species: species code (e.g. 'BFT' for Bluefin Tuna, 'YFT' for Yellowfin)
            flag: reporting country ISO3 code
            limit: max records (default 500)
        """
        limit = params.get("limit", 500)
        species_filter = params.get("species")
        flag_filter = params.get("flag")

        text: str | None = None

        # --- Try T1NC zip archives first -----------------------------------
        for zip_url in _T1NC_ZIP_URLS:
            try:
                resp = await self._request("GET", zip_url)
                import zipfile
                zf = zipfile.ZipFile(io.BytesIO(resp.content))
                # Pick the first CSV inside the zip
                csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                if csv_names:
                    text = zf.read(csv_names[0]).decode("utf-8", errors="replace")
                    logger.info("ICCAT: loaded T1NC from %s / %s", zip_url, csv_names[0])
                    break
            except Exception as exc:
                logger.debug("ICCAT zip %s failed: %s", zip_url, exc)

        # --- Fallback to EFFDIS plain CSV ----------------------------------
        if text is None:
            try:
                resp = await self._request("GET", EFFDIS_URL)
                text = resp.text
                logger.info("ICCAT: loaded EFFDIS CSV fallback")
            except Exception as exc:
                logger.error("ICCAT data fetch failed: %s", exc)
                return []

        reader = csv.DictReader(io.StringIO(text))
        observations: list[dict[str, Any]] = []

        for row in reader:
            if len(observations) >= limit:
                break

            # Filter by year range
            try:
                year = int(row.get("YearC", row.get("Year", row.get("year", "0"))))
            except (ValueError, TypeError):
                continue

            # ICCAT catch data lags 2-3 years; widen range
            min_year = time_start.year if (time_end.year - time_start.year) >= 5 else time_end.year - 5
            if year < min_year or year > time_end.year:
                continue

            species = row.get("Species", row.get("SpcCode", row.get("species", "")))
            if species_filter and species != species_filter:
                continue

            flag = row.get("Flag", row.get("FlagName", row.get("flag", "")))
            if flag_filter and flag != flag_filter:
                continue

            catch = row.get("Qty_t", row.get("Catch", row.get("catch", "0")))
            try:
                catch_val = float(catch)
            except (ValueError, TypeError):
                catch_val = 0.0

            # ICCAT areas are Atlantic regions — approximate centroid
            area = row.get("Stock", row.get("Area", row.get("area", "")))
            lon, lat = _area_centroid(area)

            observations.append({
                "obs_type": "biological",
                "timestamp": datetime(year, 1, 1),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"iccat-{species}-{flag}-{area}-{year}",
                "source_name": "ICCAT",
                "quality_score": 0.9,
                "payload": {
                    "species_code": species,
                    "flag_state": flag,
                    "gear_type": row.get("GearGrp", row.get("Gear", row.get("gear", ""))),
                    "area": area,
                    "year": year,
                    "catch_tonnes": catch_val,
                    "data_type": "nominal_catch",
                },
            })

        logger.info("ICCAT returned %d catch records", len(observations))
        return observations


def _area_centroid(area: str) -> tuple[float, float]:
    """Approximate centroid for ICCAT statistical areas."""
    area_centroids = {
        "ATW": (-40.0, 25.0),   # West Atlantic
        "ATE": (-10.0, 15.0),   # East Atlantic
        "MED": (15.0, 38.0),    # Mediterranean
        "ATS": (-20.0, -20.0),  # South Atlantic
    }
    for key, (lon, lat) in area_centroids.items():
        if key in area.upper():
            return lon, lat
    return (-30.0, 20.0)  # Default mid-Atlantic
