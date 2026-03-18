"""FRED (Federal Reserve Economic Data) adapter — BDI, commodity prices, seafood indices.

433 seafood-related series including PPI/CPI seafood, Baltic Dry Index,
oil prices, and fish/shellfish producer prices since 1974.

API docs: https://fred.stlouisfed.org/docs/api/fred/
Requires free API key from https://fred.stlouisfed.org/docs/api/api_key.html
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.stlouisfed.org/fred"

# Key maritime/seafood series
KEY_SERIES = {
    "DBDI": "Baltic Dry Index",
    "DCOILWTICO": "Crude Oil WTI ($/barrel)",
    "DCOILBRENTEU": "Crude Oil Brent ($/barrel)",
    "PCU311711311711": "PPI: Seafood product preparation/packaging",
    "WPU022104": "PPI: Fresh/frozen fish",
    "WPU02210301": "PPI: Canned fish and shellfish",
    "CUSR0000SEFJ": "CPI: Fish and seafood (US city average)",
    "PNGASEUUSDM": "Natural gas (EU, $/mmbtu)",
    "GASDESW": "Diesel fuel (US, $/gal)",
}


class FredAdapter(BaseAdapter):
    """Connector for FRED API (free API key required).

    Returns time series for maritime/seafood economic indicators.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)
        self._api_key = api_key or os.environ.get("FRED_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "fred"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch FRED time series observations.

        Extra params:
            series_id: specific FRED series ID (default: all key series)
            search: search term to find series (e.g. 'seafood')
            limit: max observations per series (default: 1000)
        """
        if not self._api_key:
            logger.warning("FRED adapter requires api_key (free at fred.stlouisfed.org)")
            return []

        series_id = params.get("series_id")
        search_term = params.get("search")
        limit = params.get("limit", 1000)

        if search_term:
            return await self._search_series(search_term, time_start, time_end, limit)

        series_list = [series_id] if series_id else list(KEY_SERIES.keys())

        observations: list[dict[str, Any]] = []

        for sid in series_list:
            url = f"{BASE_URL}/series/observations"
            query: dict[str, Any] = {
                "series_id": sid,
                "api_key": self._api_key,
                "file_type": "json",
                "observation_start": time_start.strftime("%Y-%m-%d"),
                "observation_end": time_end.strftime("%Y-%m-%d"),
                "limit": limit,
                "sort_order": "desc",
            }

            try:
                resp = await self._request("GET", url, params=query)
                data = resp.json()
            except Exception as exc:
                logger.error("FRED fetch %s failed: %s", sid, exc)
                continue

            for obs in data.get("observations", []):
                value_str = obs.get("value", ".")
                if value_str == ".":
                    continue

                try:
                    value = float(value_str)
                    ts = datetime.strptime(obs["date"], "%Y-%m-%d")
                except (ValueError, KeyError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"fred-{sid}-{obs['date']}",
                    "source_name": "FRED",
                    "quality_score": 0.98,
                    "payload": {
                        "series_id": sid,
                        "series_name": KEY_SERIES.get(sid, sid),
                        "date": obs["date"],
                        "value": value,
                        "realtime_start": obs.get("realtime_start"),
                        "realtime_end": obs.get("realtime_end"),
                    },
                })

        logger.info("FRED returned %d observations", len(observations))
        return observations

    async def _search_series(
        self,
        term: str,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search FRED for series matching a term, then fetch data."""
        url = f"{BASE_URL}/series/search"
        query = {
            "search_text": term,
            "api_key": self._api_key,
            "file_type": "json",
            "limit": 20,
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("FRED search failed: %s", exc)
            return []

        series_ids = [
            s["id"] for s in data.get("seriess", [])[:10]
            if isinstance(s, dict) and s.get("id")
        ]

        observations: list[dict[str, Any]] = []
        for sid in series_ids:
            obs = await self.fetch(
                (0, 0, 0, 0), time_start, time_end,
                series_id=sid, limit=limit // len(series_ids),
            )
            observations.extend(obs)

        return observations
