"""IMF Primary Commodity Price System (PCPS) adapter.

Monthly commodity prices including fish meal, fish oil, shrimp,
crude oil (Brent/WTI), and natural gas since 1980.

Primary source: FRED (St. Louis Fed) CSV endpoint which mirrors IMF PCPS data.
Fallback: legacy IMF SDMX JSON endpoint.
No auth required for either source.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# FRED CSV endpoint (no API key needed) — mirrors IMF PCPS monthly data
_FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# Legacy IMF SDMX endpoint — fallback (often slow/unreliable since Nov 2025)
_LEGACY_URL = "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData"

# Mapping: our commodity code -> (FRED series ID, human-readable name)
_COMMODITY_FRED_MAP = {
    "PFISH": ("PSALMUSDM", "Fish (salmon), $/kg"),
    "PSHRI": ("PSHRIUSDM", "Shrimp, $/kg"),
    "PFISHMEAL": ("PFISHMEALUSDM", "Fish meal, $/mt"),
    "POILAPSP": ("POILBREUSDM", "Crude oil (Brent), $/barrel"),
    "PNGASUS": ("PNGASUSUSDM", "Natural gas (US), $/mmbtu"),
}

# Key commodity codes (PCPS dataset) — marine-focused subset
MARINE_COMMODITIES = {
    "PFISH": "Fish (salmon) index, 2016=100",
    "PSHRI": "Shrimp index, 2016=100",
    "PFISHMEAL": "Fish meal, $/mt",
    "POILAPSP": "Crude oil (Brent), $/barrel",
    "PNGASUS": "Natural gas (US), $/mmbtu",
}


class ImfCommoditiesAdapter(BaseAdapter):
    """Connector for IMF PCPS — commodity prices (no auth required).

    Uses FRED CSV endpoint as primary source (fast, reliable) with
    legacy IMF SDMX as fallback.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=20.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "imf_commodities"

    @property
    def source_url(self) -> str:
        return "https://data.imf.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def _fetch_from_fred(
        self,
        code: str,
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch commodity price data from FRED CSV endpoint."""
        fred_info = _COMMODITY_FRED_MAP.get(code)
        if fred_info is None:
            return []

        fred_series, description = fred_info
        cosd = time_start.strftime("%Y-%m-%d")
        coed = time_end.strftime("%Y-%m-%d")
        url = _FRED_CSV_URL
        query = {"id": fred_series, "cosd": cosd, "coed": coed}

        try:
            resp = await self._request("GET", url, params=query)
            text = resp.text
        except Exception as exc:
            logger.warning("FRED CSV fetch %s (%s) failed: %s", code, fred_series, exc)
            return []

        observations: list[dict[str, Any]] = []
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return []

        # First line is header: observation_date,SERIES_ID
        for line in lines[1:]:
            parts = line.strip().split(",")
            if len(parts) < 2:
                continue
            date_str, value_str = parts[0], parts[1]
            if value_str == "." or not value_str:
                continue
            try:
                ts = datetime.strptime(date_str, "%Y-%m-%d")
                val = float(value_str)
            except (ValueError, TypeError):
                continue
            period = ts.strftime("%Y-%m")
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
                    "frequency": "M",
                    "value": val,
                    "fred_series": fred_series,
                },
            })
        return observations

    async def _fetch_from_legacy_sdmx(
        self,
        code: str,
        frequency: str,
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fallback: fetch from legacy IMF SDMX endpoint."""
        year_start = time_start.year
        year_end = time_end.year
        effective_start = max(year_start, year_end - 1)
        key = f"{frequency}..{code}"
        url = f"{_LEGACY_URL}/PCPS/{key}"
        query = {"startPeriod": str(effective_start), "endPeriod": str(year_end)}
        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("IMF legacy SDMX fetch %s failed: %s", code, exc)
            return []

        observations: list[dict[str, Any]] = []
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
                        "frequency": "M",
                        "value": val,
                    },
                })
        return observations

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        commodity = params.get("commodity")
        frequency = params.get("frequency", "M")
        limit = params.get("limit", 500)

        # Default to a single commodity (PFISH) to avoid timeout
        commodities = [commodity] if commodity else ["PFISH"]
        observations: list[dict[str, Any]] = []

        for code in commodities:
            if len(observations) >= limit:
                break

            # Strategy 1: FRED CSV (fast, reliable, no API key)
            obs = await self._fetch_from_fred(code, time_start, time_end)
            if obs:
                observations.extend(obs)
                continue

            # Strategy 2: Legacy IMF SDMX (slow, often unreliable)
            obs = await self._fetch_from_legacy_sdmx(code, frequency, time_start, time_end)
            observations.extend(obs)

        logger.info("IMF PCPS returned %d price observations", len(observations))
        return observations
