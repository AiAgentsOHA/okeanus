"""ICES (International Council for the Exploration of the Sea) adapter.

Fish stock assessments and ecosystem data for the North Atlantic.
No auth required.

API docs: https://sag.ices.dk/SAG-API/swagger/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://sag.ices.dk/SAG_API/api"

# Approximate centroids for ICES ecoregions
ECOREGION_COORDS: dict[str, tuple[float, float]] = {
    "Greater North Sea": (3.0, 56.0),
    "Celtic Seas": (-7.0, 53.0),
    "Bay of Biscay and the Iberian Coast": (-5.0, 44.0),
    "Baltic Sea": (18.0, 58.0),
    "Norwegian Sea": (5.0, 67.0),
    "Barents Sea": (35.0, 73.0),
    "Iceland": (-20.0, 65.0),
    "Greenland": (-42.0, 65.0),
    "Azores": (-27.0, 38.0),
    "Arctic Ocean": (30.0, 78.0),
    "Faroes": (-7.0, 62.0),
    "Oceanic Northeast Atlantic": (-20.0, 50.0),
    "Mediterranean": (15.0, 38.0),
    "Black Sea": (35.0, 43.0),
    "Widely distributed": (0.0, 55.0),
}

# Keywords to match stock descriptions → ecoregion name.
# Sorted longest-first so "Bay of Biscay" matches before "Baltic".
_ECOREGION_KEYWORDS: list[tuple[str, str]] = sorted(
    [
        ("north sea", "Greater North Sea"),
        ("celtic sea", "Celtic Seas"),
        ("celtic seas", "Celtic Seas"),
        ("bay of biscay", "Bay of Biscay and the Iberian Coast"),
        ("biscay", "Bay of Biscay and the Iberian Coast"),
        ("iberian", "Bay of Biscay and the Iberian Coast"),
        ("cantabrian", "Bay of Biscay and the Iberian Coast"),
        ("baltic", "Baltic Sea"),
        ("norwegian sea", "Norwegian Sea"),
        ("barents sea", "Barents Sea"),
        ("iceland", "Iceland"),
        ("greenland", "Greenland"),
        ("azores", "Azores"),
        ("arctic", "Arctic Ocean"),
        ("faroe", "Faroes"),
        ("northeast atlantic", "Oceanic Northeast Atlantic"),
        ("mediterranean", "Mediterranean"),
        ("black sea", "Black Sea"),
    ],
    key=lambda t: len(t[0]),
    reverse=True,
)


class IcesAdapter(BaseAdapter):
    """Connector for ICES Stock Assessment Graph (SAG) API (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ices"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """Fetch stock assessment summaries.

        ICES data is organized by stock/ecoregion, not by exact coordinates.
        bbox filters results to ecoregions whose approximate centroids fall
        within the bounding box.

        Extra params:
            stock_code: Specific ICES stock code (e.g. 'her.27.3a47d')
            year: Assessment year (default: time_end year)
        """
        w, s, e, n = bbox
        year = params.get("year", time_end.year)
        limit = params.get("limit", 200)

        if stock_code := params.get("stock_code"):
            return await self._fetch_stock(stock_code, year, bbox)

        # ICES data lags — try requested year, then fall back up to 3 years
        data: list[Any] = []
        for try_year in range(year, year - 4, -1):
            try:
                resp = await self._request(
                    "GET", f"{BASE_URL}/StockList",
                    params={"assessmentYear": try_year},
                )
                data = resp.json()
            except Exception as exc:
                logger.debug("ICES StockList year %d failed: %s", try_year, exc)
                continue

            records_raw = data if isinstance(data, list) else data.get("results", [data])
            if records_raw:
                logger.info("ICES: using assessment year %d", try_year)
                data = records_raw
                break
        else:
            logger.error("ICES fetch failed: no data for years %d–%d", year - 3, year)
            return []

        records = data if isinstance(data, list) else [data]
        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            # StockList doesn't return EcoRegion directly; infer from
            # StockDescription using keyword matching.
            ecoregion = rec.get("EcoRegion", rec.get("ecoRegion", ""))
            if not ecoregion:
                desc = rec.get("StockDescription", "").lower()
                for keyword, region_name in _ECOREGION_KEYWORDS:
                    if keyword in desc:
                        ecoregion = region_name
                        break
            lon, lat = ECOREGION_COORDS.get(ecoregion, (0.0, 55.0))

            # Filter by bbox
            if not (w <= lon <= e and s <= lat <= n):
                continue

            assess_year = rec.get("AssessmentYear", rec.get("assessmentYear", year))
            try:
                ts = datetime(int(assess_year), 1, 1)
            except (ValueError, TypeError):
                ts = datetime(year, 1, 1)

            stock = rec.get("StockKeyLabel", rec.get("fishStock", ""))

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ices-{stock}-{assess_year}",
                "source_name": "ICES",
                "quality_score": 0.95,
                "payload": {
                    "stock_code": stock,
                    "species_name": rec.get("SpeciesName", rec.get("speciesName", "")),
                    "ecoregion": ecoregion,
                    "assessment_year": assess_year,
                    "recruitment": rec.get("Recruitment", rec.get("recruitment")),
                    "ssb_tonnes": rec.get("SSB", rec.get("ssb")),
                    "f_mortality": rec.get("F", rec.get("fishingPressure")),
                    "catches_tonnes": rec.get("Catches", rec.get("catches")),
                    "landings_tonnes": rec.get("Landings", rec.get("landings")),
                    "advice_status": rec.get("StockStatus", rec.get("stockStatus", "")),
                    "purpose": rec.get("Purpose", ""),
                },
            })

            if len(observations) >= limit:
                break

        logger.info("ICES returned %d stock assessments", len(observations))
        return observations

    async def _fetch_stock(
        self, stock_code: str, year: int, bbox: tuple[float, float, float, float],
    ) -> list[dict[str, Any]]:
        """Fetch summary for a specific stock code."""
        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/StockSummary",
                params={"StockKeyLabel": stock_code, "year": year},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("ICES stock %s fetch failed: %s", stock_code, exc)
            return []

        records = data if isinstance(data, list) else [data]
        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            ecoregion = rec.get("EcoRegion", rec.get("ecoRegion", ""))
            lon, lat = ECOREGION_COORDS.get(ecoregion, (0.0, 55.0))

            assess_year = rec.get("AssessmentYear", rec.get("assessmentYear", year))
            try:
                ts = datetime(int(assess_year), 1, 1)
            except (ValueError, TypeError):
                ts = datetime(year, 1, 1)

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ices-{stock_code}-{assess_year}",
                "source_name": "ICES",
                "quality_score": 0.95,
                "payload": {
                    "stock_code": stock_code,
                    "species_name": rec.get("SpeciesName", rec.get("speciesName", "")),
                    "ecoregion": ecoregion,
                    "assessment_year": assess_year,
                    "recruitment": rec.get("Recruitment", rec.get("recruitment")),
                    "ssb_tonnes": rec.get("SSB", rec.get("ssb")),
                    "f_mortality": rec.get("F", rec.get("fishingPressure")),
                    "catches_tonnes": rec.get("Catches", rec.get("catches")),
                    "landings_tonnes": rec.get("Landings", rec.get("landings")),
                },
            })

        return observations
