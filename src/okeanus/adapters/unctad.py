"""UNCTAD Maritime Transport adapter — shipping economics.

World fleet size by flag, container port throughput (TEUs), seaborne
trade volumes, freight rates, Liner Shipping Connectivity Index (LSCI).

API: SDMX via UNCTADstat or UNdata.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Old UNCTAD API is dead. Use World Bank API for LSCI (same underlying data).
# UNdata SDMX fallback for other maritime indicators.
WB_API_URL = "https://api.worldbank.org/v2/country/all/indicator"
FALLBACK_URL = "https://data.un.org/ws/rest/data"

# World Bank indicator codes for UNCTAD maritime data
WB_INDICATOR_MAP = {
    "US.LSCI": "IS.SHP.GCNW.XQ",  # Liner Shipping Connectivity Index
    "US.PortContThroughput": "IS.SHP.GOOD.TU",  # Container port traffic (TEU)
}

# Key UNCTAD dataset/indicator codes
INDICATORS = {
    "US.LSCI": "Liner Shipping Connectivity Index",
    "US.FleetNatFlagDWT": "Merchant fleet by flag (DWT)",
    "US.FleetNatFlag": "Merchant fleet by flag (number)",
    "US.PortContThroughput": "Container port throughput (TEUs)",
    "US.SeaborneTrade": "International seaborne trade (mt loaded)",
    "US.MerchFleetAge": "Age of merchant fleet",
    "US.ShipBuild": "Shipbuilding deliveries (GT)",
}


class UnctadAdapter(BaseAdapter):
    """Connector for UNCTAD maritime statistics (no auth required).

    Returns global shipping data: fleet, port throughput, trade volumes,
    and the LSCI connectivity index.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "unctad"

    @property
    def source_url(self) -> str:
        return "https://unctadstat.unctad.org/"

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
        """Fetch UNCTAD maritime transport statistics.

        Extra params:
            indicator: UNCTAD indicator code (default: LSCI)
            country: ISO3 code (e.g. 'CHN', 'USA') or 'all'
            limit: max records (default: 500)
        """
        indicator = params.get("indicator", "US.LSCI")
        country = params.get("country", "")
        limit = params.get("limit", 500)
        year_start = time_start.year
        year_end = time_end.year
        # UNCTAD/World Bank data has publication lag; widen range
        if year_end - year_start < 3:
            year_start = year_end - 5

        # Try the UNCTAD API first, fallback to UNdata
        observations = await self._fetch_unctad_api(
            indicator, country, year_start, year_end, limit,
        )

        if not observations:
            observations = await self._fetch_undata(
                indicator, country, year_start, year_end, limit,
            )

        logger.info("UNCTAD returned %d observations", len(observations))
        return observations

    async def _fetch_unctad_api(
        self,
        indicator: str,
        country: str,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch UNCTAD data via World Bank API (mirrors UNCTAD LSCI etc)."""
        wb_code = WB_INDICATOR_MAP.get(indicator)
        if not wb_code:
            return []

        url = f"{WB_API_URL}/{wb_code}"
        query: dict[str, Any] = {
            "format": "json",
            "per_page": min(limit, 1000),
            "date": f"{year_start}:{year_end}",
        }
        if country:
            url = f"https://api.worldbank.org/v2/country/{country}/indicator/{wb_code}"

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception:
            return []

        # World Bank returns [metadata, records] array
        if isinstance(data, list) and len(data) >= 2:
            records = data[1] or []
        else:
            return []

        observations: list[dict[str, Any]] = []
        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            value = rec.get("value")
            if value is None:
                continue

            try:
                yr = int(rec.get("date", 0))
                ts = datetime(yr, 1, 1)
                val = float(value)
            except (ValueError, TypeError):
                continue

            ctry = rec.get("countryiso3code", rec.get("country", {}).get("id", ""))

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"unctad-{indicator}-{ctry}-{yr}",
                "source_name": "UNCTAD via World Bank",
                "quality_score": 0.90,
                "payload": {
                    "indicator": indicator,
                    "indicator_name": INDICATORS.get(indicator, indicator),
                    "country": ctry,
                    "year": yr,
                    "value": val,
                    "unit": rec.get("unit", ""),
                },
            })

        return observations

    async def _fetch_undata(
        self,
        indicator: str,
        country: str,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback to UN Data SDMX endpoint."""
        # Map UNCTAD indicator to UNdata flow
        flow = "DF_UNCTAD_LSCI" if "LSCI" in indicator else "DF_UNCTAD_MARITIME"
        url = f"{FALLBACK_URL}/{flow}/A..{country or ''}/"
        query = {
            "startPeriod": str(year_start),
            "endPeriod": str(year_end),
            "format": "jsondata",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception:
            return []

        observations: list[dict[str, Any]] = []
        datasets = data.get("dataSets", [{}])
        if not datasets:
            return []

        series = datasets[0].get("series", {})
        for key, val in series.items():
            for obs_key, obs_val in val.get("observations", {}).items():
                if not obs_val:
                    continue

                yr = year_start + int(obs_key)
                if yr > year_end:
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": datetime(yr, 1, 1),
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"undata-{flow}-{key}-{yr}",
                    "source_name": "UNCTAD via UNdata",
                    "quality_score": 0.90,
                    "payload": {
                        "indicator": indicator,
                        "indicator_name": INDICATORS.get(indicator, indicator),
                        "series_key": key,
                        "year": yr,
                        "value": obs_val[0] if isinstance(obs_val, list) else obs_val,
                    },
                })

        return observations[:limit]
