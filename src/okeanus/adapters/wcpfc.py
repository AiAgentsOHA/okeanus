"""WCPFC (Western and Central Pacific Fisheries Commission) adapter.

WCPFC manages highly migratory fish stocks in the Western and Central
Pacific Ocean — the world's largest tuna fishery by volume.

Data accessed via the Tuna Fishery Yearbook ZIP from the WCPFC scientific data page.
No auth required for aggregated public data.

Data source: https://www.wcpfc.int/sustainability/scientific-data
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# WCPFC Yearbook raw data ZIP — updated annually
YEARBOOK_ZIP_URL = "https://www.wcpfc.int/sites/default/files/2026-03/YB_WCPFC_2026-02-25.zip"
# Fallback: old direct CSV (may still work intermittently)
LEGACY_CSV_URL = "https://www.wcpfc.int/sites/default/files/science/WCPFC_YB_Annual_Catch_Estimates.csv"


class WcpfcAdapter(BaseAdapter):
    """Connector for WCPFC Pacific tuna catch data (no auth required).

    Returns catch data by species, flag, and gear for the Western
    and Central Pacific Ocean.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "wcpfc"

    @property
    def source_url(self) -> str:
        return "https://www.wcpfc.int/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def _load_csv_text(self) -> str | None:
        """Try yearbook ZIP first, fall back to legacy CSV."""
        # Try ZIP download
        try:
            resp = await self._request("GET", YEARBOOK_ZIP_URL)
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            # Prefer the full WCPFC area CSV
            csv_names = sorted(
                [n for n in zf.namelist() if n.lower().endswith(".csv")],
                key=lambda n: ("WCPFC" in n and "WCPO" not in n, len(n)),
                reverse=True,
            )
            if csv_names:
                text = zf.read(csv_names[0]).decode("utf-8", errors="replace")
                logger.info("Loaded WCPFC data from ZIP: %s", csv_names[0])
                return text
        except Exception as exc:
            logger.warning("WCPFC ZIP fetch failed: %s", exc)

        # Fallback to legacy CSV
        try:
            resp = await self._request("GET", LEGACY_CSV_URL)
            if len(resp.text) > 100:
                logger.info("Loaded WCPFC data from legacy CSV")
                return resp.text
        except Exception as exc:
            logger.warning("WCPFC legacy CSV also failed: %s", exc)

        return None

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch WCPFC tuna catch data.

        Extra params:
            species: species code (e.g. 'SKJ', 'YFT', 'BET', 'ALB')
            flag: fleet/country code
            limit: max records (default 500)
        """
        limit = params.get("limit", 500)
        species_filter = params.get("species")
        flag_filter = params.get("flag")

        text = await self._load_csv_text()
        if not text:
            logger.error("WCPFC: all data sources failed")
            return []

        reader = csv.DictReader(io.StringIO(text))
        observations: list[dict[str, Any]] = []

        for row in reader:
            if len(observations) >= limit:
                break

            try:
                year = int(row.get("YY", row.get("yy", row.get("Year", "0"))))
            except (ValueError, TypeError):
                continue

            if year < time_start.year or year > time_end.year:
                continue

            species = row.get("SP_CODE", row.get("sp_code", row.get("Species", "")))
            if species_filter and species != species_filter:
                continue

            flag = row.get("FLAG_CODE", row.get("flag_code", row.get("Flag", "")))
            if flag_filter and flag != flag_filter:
                continue

            catch = row.get("SP_MT", row.get("catch_mt", row.get("Catch", "0")))
            try:
                catch_val = float(catch) if catch else 0.0
            except (ValueError, TypeError):
                catch_val = 0.0

            gear = row.get("GEAR_CODE", row.get("gear_code", row.get("Gear", "")))
            sp_name = row.get("SP_NAME", "")

            # Aggregated data — use center of WCPFC convention area
            lon, lat = 160.0, 0.0

            observations.append({
                "obs_type": "biological",
                "timestamp": datetime(year, 1, 1),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"wcpfc-{species}-{flag}-{gear}-{year}",
                "source_name": "WCPFC",
                "quality_score": 0.9,
                "payload": {
                    "species_code": species,
                    "species_name": sp_name,
                    "flag_state": flag,
                    "gear_type": gear,
                    "year": year,
                    "catch_tonnes": catch_val,
                    "data_type": "annual_catch",
                },
            })

        logger.info("WCPFC returned %d catch records", len(observations))
        return observations
