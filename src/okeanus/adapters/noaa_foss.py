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

        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("Year") or rec.get("year")
            if year is None:
                continue

            try:
                yr = int(year)
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            pounds = rec.get("Pounds") or rec.get("pounds") or rec.get("Live Pounds")
            dollars = rec.get("Dollars") or rec.get("dollars") or rec.get("Value")

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [-98.5, 39.8]},
                "source_id": f"foss-land-{rec.get('Species','')}-{rec.get('State','')}-{yr}",
                "source_name": "NOAA FOSS",
                "quality_score": 0.95,
                "payload": {
                    "type": "landings",
                    "species": rec.get("Species") or rec.get("species_name", ""),
                    "state": rec.get("State") or rec.get("state_name", ""),
                    "port": rec.get("Port") or rec.get("port_name", ""),
                    "pounds": pounds,
                    "dollars": dollars,
                    "price_per_lb": (float(dollars) / float(pounds)) if pounds and dollars else None,
                    "year": yr,
                    "collection": rec.get("Collection") or rec.get("collection_type", ""),
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

        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("Year") or rec.get("year")
            month = rec.get("Month") or rec.get("month") or 1

            try:
                ts = datetime(int(year), int(month), 1)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [-98.5, 39.8]},
                "source_id": f"foss-trade-{rec.get('Name','')}-{year}-{month}",
                "source_name": "NOAA FOSS",
                "quality_score": 0.93,
                "payload": {
                    "type": "foreign_trade",
                    "product": rec.get("Name") or rec.get("product", ""),
                    "country": rec.get("Country") or rec.get("country", ""),
                    "flow": rec.get("Association") or rec.get("flow", ""),
                    "kilograms": rec.get("Kilograms") or rec.get("kilograms"),
                    "dollars": rec.get("Dollars") or rec.get("dollars"),
                    "year": int(year),
                    "month": int(month),
                },
            })

        logger.info("NOAA FOSS trade returned %d records", len(observations))
        return observations
