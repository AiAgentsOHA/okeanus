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

ARCGIS_URL = "https://www.coast.noaa.gov/arcgis/rest/services/enow/OceanEconomybyIndicator/MapServer"

# Layer IDs for state-level data by indicator
STATE_LAYERS = {
    "Employment": 9,
    "Wages": 25,
    "GDP": 41,
    "Establishments": 57,
}

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
        limit = params.get("limit", 500)
        year_start = time_start.year
        year_end = time_end.year

        # Use ArcGIS MapServer — layer 1 is AllOceanSectors_Employment
        # which includes Employment, Wages, GDP, Establishments in attributes
        layer_id = 1  # AllOceanSectors_Employment
        url = f"{ARCGIS_URL}/{layer_id}/query"

        # ENOW data lags several years; widen range to include older data
        if year_start > 2010:
            year_start = 2010
        # Build where clause for year range
        where_parts = [f"Year>={year_start}", f"Year<={year_end}"]
        where = " AND ".join(where_parts)

        query: dict[str, Any] = {
            "where": where,
            "outFields": "GeoID,GeoName,OceanSect_ID,OceanSector,Year,Employment,Wages,GDP,Establishments",
            "returnGeometry": "false",
            "resultRecordCount": limit,
            "f": "json",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA ENOW fetch failed: %s", exc)
            return []

        features = data.get("features", [])

        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        observations: list[dict[str, Any]] = []

        for feat in features:
            attrs = feat.get("attributes", {})
            if not attrs:
                continue

            year = attrs.get("Year")
            try:
                yr = int(year)
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            fips = str(attrs.get("GeoID", ""))
            geo_name = attrs.get("GeoName", "")
            sect = attrs.get("OceanSector", "All Ocean Sectors")

            gdp = attrs.get("GDP")
            employment = attrs.get("Employment")
            wages = attrs.get("Wages")
            establishments = attrs.get("Establishments")

            # Skip suppressed data (-9999 means suppressed)
            if gdp == -9999:
                gdp = None
            if employment == -9999:
                employment = None
            if wages == -9999:
                wages = None
            if establishments == -9999:
                establishments = None

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [center_lon, center_lat],
                },
                "source_id": f"enow-{fips}-{sect}-{yr}",
                "source_name": "NOAA ENOW",
                "quality_score": 0.95,
                "payload": {
                    "fips": fips,
                    "geo_name": geo_name,
                    "geo_type": "State",
                    "sector": sect,
                    "year": yr,
                    "gdp": gdp,
                    "employment": employment,
                    "wages": wages,
                    "establishments": establishments,
                },
            })

        logger.info("NOAA ENOW returned %d observations", len(observations))
        return observations
