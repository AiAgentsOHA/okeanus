"""NOAA FOSS (Fisheries One Stop Shop) adapter.

US commercial fisheries landings (value $/kg) since 1950 and
foreign trade data since 1975.

Data: REST/web query at fisheries.noaa.gov.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fisheries.noaa.gov/foss/f"
API_URL = "https://apps-st.fisheries.noaa.gov/ods/foss"

# Endpoints
LANDINGS_URL = f"{API_URL}/landings"
TRADE_URL = f"{API_URL}/trade"


class NoaaFossAdapter(BaseAdapter):
    """Connector for NOAA FOSS — US fisheries landings + trade (no auth).

    Returns commercial landings (species, port, value, weight) and
    foreign seafood trade data for the United States.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_foss"

    @property
    def source_url(self) -> str:
        return "https://www.fisheries.noaa.gov/foss/"

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
        """Fetch NOAA FOSS landings or trade data.

        Extra params:
            endpoint: 'landings' (default) or 'trade'
            species: species name filter
            state: US state name (for landings)
            limit: max records (default: 500)
        """
        endpoint = params.get("endpoint", "landings")
        species = params.get("species")
        state = params.get("state")
        limit = params.get("limit", 500)

        year_start = time_start.year
        year_end = time_end.year

        if endpoint == "trade":
            return await self._fetch_trade(species, year_start, year_end, limit)

        return await self._fetch_landings(species, state, year_start, year_end, limit)

    async def _fetch_landings(
        self,
        species: str | None,
        state: str | None,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch US commercial fisheries landings."""
        query: dict[str, Any] = {
            "start": year_start,
            "end": year_end,
            "format": "json",
            "top": limit,
        }
        if species:
            query["species"] = species
        if state:
            query["state"] = state

        try:
            resp = await self._request("GET", LANDINGS_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA FOSS landings fetch failed: %s", exc)
            return []

        # API returns {items: [...], hasMore, limit, offset, count}
        records = data.get("items", []) if isinstance(data, dict) else data
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("year") or rec.get("Year")
            if year is None:
                continue

            try:
                yr = int(year)
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            pounds = rec.get("pounds") or rec.get("Pounds")
            dollars = rec.get("dollars") or rec.get("Dollars")
            species = rec.get("ts_afs_name") or rec.get("Species") or rec.get("species_name", "")
            state_name = rec.get("state_name") or rec.get("State") or ""
            region = rec.get("region_name") or rec.get("Region") or ""
            collection = rec.get("collection") or rec.get("Collection") or ""

            price_per_lb = None
            try:
                if pounds and dollars:
                    price_per_lb = float(dollars) / float(pounds)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [-98.5, 39.8]},
                "source_id": f"foss-land-{species}-{state_name}-{yr}",
                "source_name": "NOAA FOSS",
                "quality_score": 0.95,
                "payload": {
                    "type": "landings",
                    "species": species,
                    "state": state_name,
                    "region": region,
                    "pounds": pounds,
                    "dollars": dollars,
                    "price_per_lb": price_per_lb,
                    "year": yr,
                    "collection": collection,
                    "source": rec.get("source", ""),
                },
            })

        logger.info("NOAA FOSS landings returned %d records", len(observations))
        return observations

    async def _fetch_trade(
        self,
        species: str | None,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch US seafood foreign trade data."""
        query: dict[str, Any] = {
            "start": year_start,
            "end": year_end,
            "format": "json",
            "top": limit,
        }
        if species:
            query["species"] = species

        try:
            resp = await self._request("GET", TRADE_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA FOSS trade fetch failed: %s", exc)
            return []

        # API returns {items: [...], hasMore, limit, offset, count}
        records = data.get("items", []) if isinstance(data, dict) else data
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("year") or rec.get("Year")
            month = rec.get("month") or rec.get("Month") or 1

            try:
                ts = datetime(int(year), int(month), 1)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [-98.5, 39.8]},
                "source_id": f"foss-trade-{rec.get('name', rec.get('Name',''))}-{year}-{month}",
                "source_name": "NOAA FOSS",
                "quality_score": 0.93,
                "payload": {
                    "type": "foreign_trade",
                    "product": rec.get("name") or rec.get("Name") or rec.get("product", ""),
                    "country": rec.get("country") or rec.get("Country", ""),
                    "flow": rec.get("association") or rec.get("Association") or rec.get("flow", ""),
                    "kilograms": rec.get("kilograms") or rec.get("Kilograms"),
                    "dollars": rec.get("dollars") or rec.get("Dollars"),
                    "year": int(year),
                    "month": int(month),
                },
            })

        logger.info("NOAA FOSS trade returned %d records", len(observations))
        return observations
