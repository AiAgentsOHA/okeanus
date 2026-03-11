"""ICES SAG (Stock Assessment Graphs) adapter.

Northeast Atlantic stock assessments — fishing mortality, spawning
biomass, recruitment, reference points, and advice since 2014.

API: REST at sag.ices.dk.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://sag.ices.dk/SAG_API/api"


class IcesSagAdapter(BaseAdapter):
    """Connector for ICES SAG — NE Atlantic stock assessments (no auth).

    Returns stock assessment data including fishing mortality (F),
    spawning stock biomass (SSB), recruitment (R), and reference points.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ices_sag"

    @property
    def source_url(self) -> str:
        return "https://sag.ices.dk/"

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
        """Fetch ICES stock assessment data.

        Extra params:
            stock_code: ICES stock code (e.g. 'cod.27.47d20')
            year: assessment year (default: latest)
            limit: max records (default: 500)
        """
        stock_code = params.get("stock_code")
        year = params.get("year", time_end.year)
        limit = params.get("limit", 500)

        if stock_code:
            return await self._fetch_stock(stock_code, year, time_start, time_end, limit)

        return await self._fetch_summary(year, time_start, time_end, limit)

    async def _fetch_stock(
        self,
        stock_code: str,
        year: int,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch detailed data for a specific stock."""
        url = f"{BASE_URL}/StockDownload"
        query = {"stockCode": stock_code, "assessmentYear": year}

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("ICES SAG stock %s fetch failed: %s", stock_code, exc)
            return []

        records = data if isinstance(data, list) else data.get("data", [])
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            data_year = rec.get("Year") or rec.get("year")
            try:
                yr = int(data_year)
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 55]},
                "source_id": f"ices-sag-{stock_code}-{yr}",
                "source_name": "ICES SAG",
                "quality_score": 0.95,
                "payload": {
                    "stock_code": stock_code,
                    "year": yr,
                    "assessment_year": year,
                    "fishing_mortality": rec.get("F") or rec.get("fishingPressure"),
                    "ssb": rec.get("SSB") or rec.get("stockSize"),
                    "recruitment": rec.get("Recruitment") or rec.get("recruitment"),
                    "catches": rec.get("Catches") or rec.get("catches"),
                    "landings": rec.get("Landings") or rec.get("landings"),
                    "discards": rec.get("Discards") or rec.get("discards"),
                    "f_msy": rec.get("FMSY") or rec.get("fmsy"),
                    "blim": rec.get("Blim") or rec.get("blim"),
                    "bpa": rec.get("Bpa") or rec.get("bpa"),
                    "stock_status": rec.get("StockStatus") or rec.get("status", ""),
                },
            })

        logger.info("ICES SAG %s returned %d data points", stock_code, len(observations))
        return observations

    async def _fetch_summary(
        self,
        year: int,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch summary of all stock assessments for a year."""
        url = f"{BASE_URL}/StockList"
        query: dict[str, Any] = {"assessmentYear": year}

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("ICES SAG summary fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", [])
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            stock_code = rec.get("StockKeyLabel") or rec.get("stockCode", "")

            observations.append({
                "obs_type": "economic",
                "timestamp": datetime(year, 1, 1),
                "geometry": {"type": "Point", "coordinates": [0, 55]},
                "source_id": f"ices-sag-summary-{stock_code}-{year}",
                "source_name": "ICES SAG",
                "quality_score": 0.95,
                "payload": {
                    "stock_code": stock_code,
                    "species": rec.get("SpeciesCommonName") or rec.get("species", ""),
                    "scientific_name": rec.get("SpeciesScientificName", ""),
                    "ecoregion": rec.get("EcoRegion") or rec.get("ecoregion", ""),
                    "data_category": rec.get("DataCategory"),
                    "assessment_year": year,
                    "advice_status": rec.get("AdviceStatus", ""),
                },
            })

        logger.info("ICES SAG summary returned %d stocks for %d", len(observations), year)
        return observations
