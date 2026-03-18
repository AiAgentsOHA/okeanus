"""OpenFisheries adapter — global fisheries landings data via World Bank API.

Provides country-level annual fish capture production data sourced from the
FAO FishStatJ database. The original openfisheries.org API (HTTP 526) has
been replaced with the World Bank Indicators API (ER.FSH.CAPT.MT) which
exposes the same underlying FAO capture production data. No auth required.

World Bank indicator: https://data.worldbank.org/indicator/ER.FSH.CAPT.MT
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# World Bank API v2 — FAO capture fisheries production (metric tons)
_WB_API = "https://api.worldbank.org/v2"
_INDICATOR = "ER.FSH.CAPT.MT"


class OpenFisheriesAdapter(BaseAdapter):
    """Connector for global fisheries landings via World Bank API (no auth).

    Uses World Bank indicator ER.FSH.CAPT.MT (FAO capture fisheries
    production in metric tons) as a reliable replacement for the defunct
    openfisheries.org API.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "openfisheries"

    @property
    def source_url(self) -> str:
        return f"https://data.worldbank.org/indicator/{_INDICATOR}"

    @property
    def update_frequency(self) -> str:
        return "annual"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch global fisheries capture production data.

        Extra params:
            country: ISO3 country code or semicolon-separated list
                     (e.g. 'USA', 'NOR', 'USA;NOR;CHN').
                     Defaults to 'all' (all countries).
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        country = params.get("country", "all")

        start_year = time_start.year
        end_year = time_end.year

        # World Bank fisheries data is typically 2-3 years behind.  When the
        # requested window has no data (all values null), automatically widen
        # backwards up to 5 extra years so the adapter doesn't return empty
        # just because the user asked for "last 365 days".
        effective_start = max(start_year - 5, 2000)

        url = f"{_WB_API}/country/{country}/indicator/{_INDICATOR}"
        wb_params: dict[str, Any] = {
            "format": "json",
            "date": f"{effective_start}:{end_year}",
            "per_page": min(limit * 3, 1000),  # over-fetch to account for nulls
        }

        try:
            resp = await self._request("GET", url, params=wb_params)
            data = resp.json()
        except Exception as exc:
            logger.error("OpenFisheries (World Bank) fetch failed: %s", exc)
            return []

        # World Bank JSON: [ {metadata}, [ {record}, ... ] ]
        if not isinstance(data, list) or len(data) < 2:
            logger.warning("OpenFisheries: unexpected World Bank response format")
            return []

        records = data[1]
        if not isinstance(records, list):
            return []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            value = rec.get("value")
            date_str = rec.get("date", "")

            if value is None:
                continue

            try:
                year = int(date_str)
                catch = float(value)
            except (ValueError, TypeError):
                continue

            if year < effective_start or year > end_year:
                continue

            ts = datetime(year, 7, 1, tzinfo=timezone.utc)
            ctry_info = rec.get("country", {})
            ctry_code = rec.get("countryiso3code", "")
            ctry_name = ctry_info.get("value", "") if isinstance(ctry_info, dict) else ""

            observations.append({
                "obs_type": "fisheries",
                "timestamp": ts,
                "geometry": None,
                "source_id": f"openfisheries-{ctry_code or 'global'}-{year}",
                "source_name": "OpenFisheries",
                "quality_score": 0.9,
                "payload": {
                    "year": year,
                    "catch_tonnes": catch,
                    "country": ctry_code or "global",
                    "country_name": ctry_name,
                    "species": "all",
                    "indicator": _INDICATOR,
                },
            })

            if len(observations) >= limit:
                break

        logger.info("OpenFisheries returned %d records", len(observations))
        return observations
