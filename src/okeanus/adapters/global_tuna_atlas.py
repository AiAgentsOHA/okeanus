"""Global Tuna Atlas adapter — harmonized catch data from all 5 tuna RFMOs.

The FIRMS Global Tuna Atlas (hosted on Zenodo) provides harmonized Level 0
catch data from ICCAT, IOTC, WCPFC, IATTC, and CCAMLR in a single CSV
using the CWP Reference Harmonization standard. No auth required.

Source: https://zenodo.org/records/17494424 (annual, 1918-2023)
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Zenodo record 17494424 is the latest version with actual files.
# The file is a ZIP containing a CSV.
DATASET_URL = (
    "https://zenodo.org/records/17494424/files/"
    "global_nominal_catch_firms_level0_public.zip?download=1"
)

# Fallback: older version with direct CSV access
FALLBACK_CSV_URL = (
    "https://zenodo.org/api/records/11410529/files/"
    "global_nominal_catch_firms_level0_harmonized.csv/content"
)

# Common tuna species codes
TUNA_SPECIES = {
    "YFT": "Yellowfin tuna",
    "BET": "Bigeye tuna",
    "SKJ": "Skipjack tuna",
    "ALB": "Albacore",
    "SBF": "Southern bluefin tuna",
    "BFT": "Atlantic bluefin tuna",
    "PBF": "Pacific bluefin tuna",
    "SWO": "Swordfish",
    "MLS": "Striped marlin",
    "BUM": "Blue marlin",
}


class GlobalTunaAtlasAdapter(BaseAdapter):
    """Connector for FIRMS Global Tuna Atlas (all 5 RFMOs harmonized)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "global_tuna_atlas"

    @property
    def source_url(self) -> str:
        return "https://zenodo.org/records/15286474"

    @property
    def update_frequency(self) -> str:
        return "annual"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch harmonized tuna catch data from FIRMS Global Tuna Atlas.

        Extra params:
            dataset: 'annual' (default), 'monthly_5deg', 'monthly_1deg_surface'
            species: Species code filter (e.g. 'YFT', 'SKJ')
            rfmo: RFMO filter (e.g. 'ICCAT', 'IOTC', 'WCPFC', 'IATTC', 'CCAMLR')
            limit: Max records (default 200)
        """
        limit = params.get("limit", 200)
        species_filter = params.get("species", "").upper()
        rfmo_filter = params.get("rfmo", "").upper()
        w, s, e, n = bbox

        text = await self._download_csv()
        if not text:
            return []

        observations: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            if len(observations) >= limit:
                break

            # Parse year
            year_str = row.get("year", row.get("time_start", ""))
            try:
                year = int(str(year_str).strip()[:4])
            except (ValueError, TypeError):
                continue

            ts = datetime(year, 7, 1, tzinfo=timezone.utc)
            # Tuna atlas data lags 2-3 years; widen range to 5 years
            min_year = time_start.year if (time_end.year - time_start.year) >= 5 else time_end.year - 5
            if year < min_year or year > time_end.year:
                continue

            # Parse coordinates (grid center)
            lat_str = row.get("latitude", row.get("geographic_identifier", ""))
            lon_str = row.get("longitude", "")

            # Some datasets encode location as geographic_identifier
            if not lon_str and "x" in str(lat_str).lower():
                continue  # Skip non-numeric geographic identifiers

            try:
                lat = float(lat_str)
                lon = float(lon_str) if lon_str else 0
            except (ValueError, TypeError):
                # For annual data, coordinates may not be present
                lat, lon = 0, 0

            # Spatial filter (skip if coordinates available and outside bbox)
            if lat != 0 and lon != 0:
                if not (w <= lon <= e and s <= lat <= n):
                    continue

            geometry = (
                {"type": "Point", "coordinates": [lon, lat]}
                if lat != 0 and lon != 0
                else None
            )

            # Species filter
            species = row.get("species", row.get("species_code", ""))
            if species_filter and species_filter != species.upper():
                continue

            # RFMO filter
            rfmo = row.get("source_authority", row.get("rfmo", ""))
            if rfmo_filter and rfmo_filter not in rfmo.upper():
                continue

            # Parse catch value
            catch_str = row.get("value", row.get("catch", "0"))
            try:
                catch_value = float(catch_str) if catch_str else 0
            except (ValueError, TypeError):
                catch_value = 0

            gear = row.get("gear_type", row.get("gear", ""))
            flag = row.get("fishing_fleet", row.get("flag", ""))
            unit = row.get("unit", row.get("measurement_unit", ""))

            observations.append({
                "obs_type": "fisheries_catch",
                "timestamp": ts,
                "geometry": geometry,
                "source_id": f"gta-{rfmo}-{year}-{species}-{flag}",
                "source_name": f"Global Tuna Atlas ({rfmo})",
                "quality_score": 0.9,
                "payload": {
                    "year": year,
                    "species_code": species,
                    "species_name": TUNA_SPECIES.get(species.upper(), species),
                    "rfmo": rfmo,
                    "gear": gear,
                    "flag": flag,
                    "catch_value": catch_value,
                    "unit": unit,
                    "month": row.get("month", ""),
                },
            })

        logger.info("Global Tuna Atlas returned %d catch records", len(observations))
        return observations

    async def _download_csv(self) -> str:
        """Download CSV from Zenodo ZIP, falling back to older direct CSV."""
        # Try ZIP download first (latest version)
        try:
            resp = await self._request("GET", DATASET_URL)
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if csv_names:
                return zf.read(csv_names[0]).decode("utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Global Tuna Atlas ZIP failed: %s, trying fallback", exc)

        # Fallback to older direct CSV
        try:
            resp = await self._request("GET", FALLBACK_CSV_URL)
            return resp.text
        except Exception as exc:
            logger.error("Global Tuna Atlas fetch failed: %s", exc)
            return ""
