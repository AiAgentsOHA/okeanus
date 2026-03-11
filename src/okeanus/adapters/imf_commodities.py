"""IMF Primary Commodity Price System (PCPS) adapter.

Monthly commodity prices including fish meal, fish oil, shrimp,
crude oil (Brent/WTI), and natural gas since 1980.

API: SDMX endpoint at data.imf.org.
No auth required (also mirrored on FRED).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.imf.org/external/datamapper/api/v1"
SDMX_URL = "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData"

# Key commodity codes (PCPS dataset)
MARINE_COMMODITIES = {
    "PFISH": "Fish (salmon) index, 2016=100",
    "PSHRI": "Shrimp index, 2016=100",
    "PFISHMEAL": "Fish meal, $/mt",
    "PPOIL": "Crude oil (avg), $/barrel",
    "PNGASEU": "Natural gas (EU), $/mmbtu",
    "PNGASJP": "Natural gas (Japan), $/mmbtu",
    "PNGASUS": "Natural gas (US), $/mmbtu",
    "POILAPSP": "Crude oil (Brent), $/barrel",
    "POILWTI": "Crude oil (WTI), $/barrel",
}


class ImfCommoditiesAdapter(BaseAdapter):
    """Connector for IMF PCPS — commodity prices (no auth required).

    Returns monthly price indices for seafood, energy, and related
    marine commodities.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "imf_commodities"

    @property
    def source_url(self) -> str:
        return "https://data.imf.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch IMF commodity prices.

        Extra params:
            commodity: specific PCPS code (default: all marine commodities)
            frequency: 'M' (monthly), 'Q' (quarterly), 'A' (annual)
        """
        commodity = params.get("commodity")
        frequency = params.get("frequency", "M")

        commodities = [commodity] if commodity else list(MARINE_COMMODITIES.keys())
        year_start = time_start.year
        year_end = time_end.year

        observations: list[dict[str, Any]] = []

        # Try SDMX endpoint
        for code in commodities:
            key = f"{frequency}..{code}"
            url = f"{SDMX_URL}/PCPS/{key}"
            query: dict[str, Any] = {
                "startPeriod": f"{year_start}",
                "endPeriod": f"{year_end}",
            }

            try:
                resp = await self._request("GET", url, params=query)
                data = resp.json()
            except Exception as exc:
                logger.warning("IMF SDMX fetch %s failed: %s", code, exc)
                # Fallback to DataMapper API
                obs = await self._fetch_datamapper(code, year_start, year_end)
                observations.extend(obs)
                continue

            # Parse SDMX-JSON compact format
            ds = data.get("CompactData", {}).get("DataSet", {})
            series = ds.get("Series", {})

            if isinstance(series, dict):
                series = [series]
            elif not isinstance(series, list):
                series = []

            for s in series:
                obs_list = s.get("Obs", [])
                if isinstance(obs_list, dict):
                    obs_list = [obs_list]

                for obs in obs_list:
                    period = obs.get("@TIME_PERIOD", "")
                    value = obs.get("@OBS_VALUE")
                    if value is None:
                        continue

                    try:
                        val = float(value)
                        # Parse period: 2024-01, 2024-Q1, 2024
                        if "-" in period and "Q" not in period:
                            parts = period.split("-")
                            ts = datetime(int(parts[0]), int(parts[1]), 1)
                        elif "Q" in period:
                            yr, q = period.split("-Q")
                            ts = datetime(int(yr), int(q) * 3 - 2, 1)
                        else:
                            ts = datetime(int(period), 1, 1)
                    except (ValueError, TypeError, IndexError):
                        continue

                    if ts < time_start or ts > time_end:
                        continue

                    observations.append({
                        "obs_type": "economic",
                        "timestamp": ts,
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                        "source_id": f"imf-{code}-{period}",
                        "source_name": "IMF PCPS",
                        "quality_score": 0.97,
                        "payload": {
                            "commodity_code": code,
                            "commodity_name": MARINE_COMMODITIES.get(code, code),
                            "period": period,
                            "frequency": frequency,
                            "value": val,
                            "unit": "index (2016=100)" if code.startswith("P") and "MEAL" not in code else "$/mt or $/barrel",
                        },
                    })

        logger.info("IMF PCPS returned %d price observations", len(observations))
        return observations

    async def _fetch_datamapper(
        self, code: str, year_start: int, year_end: int,
    ) -> list[dict[str, Any]]:
        """Fallback: fetch from IMF DataMapper JSON API."""
        url = f"{BASE_URL}/PCPS/{code}"

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("IMF DataMapper %s failed: %s", code, exc)
            return []

        values = data.get("values", {}).get(code, {})
        if not isinstance(values, dict):
            return []

        observations: list[dict[str, Any]] = []
        for country_or_global, years_data in values.items():
            if not isinstance(years_data, dict):
                continue
            for year_str, val in years_data.items():
                try:
                    yr = int(year_str)
                    if yr < year_start or yr > year_end:
                        continue
                    observations.append({
                        "obs_type": "economic",
                        "timestamp": datetime(yr, 1, 1),
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                        "source_id": f"imf-dm-{code}-{yr}",
                        "source_name": "IMF PCPS",
                        "quality_score": 0.95,
                        "payload": {
                            "commodity_code": code,
                            "commodity_name": MARINE_COMMODITIES.get(code, code),
                            "year": yr,
                            "value": float(val),
                        },
                    })
                except (ValueError, TypeError):
                    continue

        return observations
