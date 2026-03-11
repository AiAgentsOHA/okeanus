"""NOAA ENOW (Economics: National Ocean Watch) adapter.

The definitive US ocean economy dataset — GDP, employment, wages, and
establishments for 6 sectors by county, 2005-present.

Data source: https://coast.noaa.gov/digitalcoast/data/enow.html
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://coast.noaa.gov/api/enow"

SECTORS = [
    "All Ocean Sectors",
    "Living Resources",
    "Marine Construction",
    "Marine Transportation",
    "Offshore Mineral Extraction",
    "Ship & Boat Building",
    "Tourism & Recreation",
]


class NoaaEnowAdapter(BaseAdapter):
    """Connector for NOAA ENOW — US ocean economy by county (no auth required).

    Returns GDP, employment, wages, and establishment counts for ocean
    economy sectors at national, state, and county levels.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_enow"

    @property
    def source_url(self) -> str:
        return "https://coast.noaa.gov/digitalcoast/data/enow.html"

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
        """Fetch ENOW ocean economy data.

        Extra params:
            state_fips: state FIPS code (e.g. '06' for California)
            county_fips: county FIPS code
            sector: ENOW sector name
            geo_type: 'State', 'County', or 'National' (default: 'State')
        """
        state_fips = params.get("state_fips")
        county_fips = params.get("county_fips")
        sector = params.get("sector")
        geo_type = params.get("geo_type", "State")
        year_start = time_start.year
        year_end = time_end.year

        query: dict[str, Any] = {
            "geoType": geo_type,
            "format": "json",
        }
        if state_fips:
            query["stateFips"] = state_fips
        if county_fips:
            query["countyFips"] = county_fips
        if sector:
            query["sector"] = sector

        try:
            resp = await self._request("GET", f"{BASE_URL}/data", params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA ENOW fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(records, list):
            records = []

        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("Year") or rec.get("year")
            try:
                yr = int(year)
                if yr < year_start or yr > year_end:
                    continue
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            fips = rec.get("GeoID") or rec.get("FIPS") or ""
            geo_name = rec.get("GeoName") or rec.get("Name") or ""
            sect = rec.get("Sector") or rec.get("sector") or "All"

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        rec.get("Longitude") or center_lon,
                        rec.get("Latitude") or center_lat,
                    ],
                },
                "source_id": f"enow-{fips}-{sect}-{yr}",
                "source_name": "NOAA ENOW",
                "quality_score": 0.95,
                "payload": {
                    "fips": fips,
                    "geo_name": geo_name,
                    "geo_type": geo_type,
                    "sector": sect,
                    "year": yr,
                    "gdp": rec.get("GDP") or rec.get("gdp"),
                    "employment": rec.get("Employment") or rec.get("employment"),
                    "wages": rec.get("Wages") or rec.get("wages"),
                    "establishments": rec.get("Establishments") or rec.get("establishments"),
                    "state_name": rec.get("StateName") or rec.get("state_name", ""),
                },
            })

        logger.info("NOAA ENOW returned %d observations", len(observations))
        return observations
