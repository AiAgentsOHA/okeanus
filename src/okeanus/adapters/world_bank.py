"""World Bank WDI adapter — blue economy indicators.

Indicators include fisheries contribution to GDP, marine protected areas,
fish exports, coastal population, logistics performance index, and more.

API docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2"

# Key blue economy indicator codes
BLUE_INDICATORS = {
    "ER.MRN.PTMR.ZS": "Marine protected areas (% territorial waters)",
    "NE.EXP.GNFS.ZS": "Exports of goods and services (% of GDP)",
    "AG.LND.FRST.ZS": "Forest area (% land) — coastal proxy",
    "EN.ATM.CO2E.KT": "CO2 emissions (kt) — maritime transport component",
    "IS.SHP.GOOD.TU": "Container port traffic (TEU)",
    "SH.H2O.SMDW.ZS": "People using safely managed drinking water (%)",
    "SP.POP.TOTL": "Population total — for coastal % calc",
    "NY.GDP.MKTP.CD": "GDP current USD — denominator",
    "LP.LPI.OVRL.XQ": "Logistics performance index (1=low, 5=high)",
    "IC.IMP.DURS": "Time to import (days)",
    "IC.EXP.DURS": "Time to export (days)",
}


class WorldBankAdapter(BaseAdapter):
    """Connector for World Bank WDI API (no auth required).

    Returns country-level blue economy indicators as time series.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "world_bank"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """Fetch World Bank blue economy indicators.

        Extra params:
            indicator: WDI indicator code (default: all blue indicators)
            country: ISO2 or ISO3 code, or 'all' (default: 'all')
            limit: Max records per indicator (default: 500)
        """
        indicator = params.get("indicator")
        country = params.get("country", "all")
        limit = params.get("limit", 500)

        indicators = [indicator] if indicator else list(BLUE_INDICATORS.keys())
        year_start = time_start.year
        year_end = time_end.year

        observations: list[dict[str, Any]] = []

        for ind_code in indicators:
            url = f"{BASE_URL}/country/{country}/indicator/{ind_code}"
            query: dict[str, Any] = {
                "format": "json",
                "per_page": limit,
                "date": f"{year_start}:{year_end}",
            }

            try:
                resp = await self._request("GET", url, params=query)
                data = resp.json()
            except Exception as exc:
                logger.error("World Bank fetch %s failed: %s", ind_code, exc)
                continue

            if not isinstance(data, list) or len(data) < 2:
                continue

            records = data[1] if isinstance(data[1], list) else []

            for rec in records:
                if not isinstance(rec, dict) or rec.get("value") is None:
                    continue

                ctry = rec.get("country", {})
                year = rec.get("date", "")

                try:
                    ts = datetime(int(year), 1, 1)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [
                            rec.get("longitude") or 0.0,
                            rec.get("latitude") or 0.0,
                        ],
                    },
                    "source_id": f"wb-{ind_code}-{ctry.get('id','')}-{year}",
                    "source_name": "World Bank WDI",
                    "quality_score": 0.95,
                    "payload": {
                        "indicator_code": ind_code,
                        "indicator_name": BLUE_INDICATORS.get(
                            ind_code, rec.get("indicator", {}).get("value", ""),
                        ),
                        "country_code": ctry.get("id", ""),
                        "country_name": ctry.get("value", ""),
                        "year": year,
                        "value": rec["value"],
                        "unit": rec.get("unit", ""),
                        "decimal": rec.get("decimal", 0),
                    },
                })

        logger.info("World Bank returned %d observations", len(observations))
        return observations
