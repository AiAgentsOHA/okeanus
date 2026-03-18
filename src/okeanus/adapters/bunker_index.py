"""Bunker fuel price adapter — marine fuel price data.

Daily marine fuel prices (MGO, IFO 180, IFO 380) from
USDA Agricultural Transportation open data (Socrata API).

API: Socrata REST at agtransport.usda.gov.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# USDA Agricultural Transportation Socrata API — daily bunker fuel prices
SOCRATA_URL = "https://agtransport.usda.gov/resource/4v3x-mj86.json"

# Fuel types available in the dataset
FUEL_COLUMNS = {
    "MGO": "marine_gas_oil",
    "IFO180": "intermdiate_fuel_oil_180cst",
    "IFO380": "intermdiate_fuel_oil_380cst",
}

FUEL_NAMES = {
    "MGO": "Marine Gas Oil",
    "IFO180": "Intermediate Fuel Oil 180cSt",
    "IFO380": "Intermediate Fuel Oil 380cSt",
}


class BunkerIndexAdapter(BaseAdapter):
    """Connector for bunker fuel prices via USDA Socrata (no auth required).

    Returns daily MGO, IFO 180, and IFO 380 price data.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "bunker_index"

    @property
    def source_url(self) -> str:
        return "https://agtransport.usda.gov/"

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
        """Fetch bunker fuel prices from USDA Socrata API.

        Extra params:
            fuel_type: 'MGO', 'IFO180', 'IFO380', or 'all' (default: 'all')
            limit: max records (default: 200)
        """
        fuel_type = params.get("fuel_type", "all")
        limit = params.get("limit", 200)

        start_str = time_start.strftime("%Y-%m-%dT00:00:00.000")
        end_str = time_end.strftime("%Y-%m-%dT23:59:59.999")

        query: dict[str, Any] = {
            "$where": f"day >= '{start_str}' AND day <= '{end_str}'",
            "$order": "day DESC",
            "$limit": limit,
        }

        try:
            resp = await self._request("GET", SOCRATA_URL, params=query)
            records = resp.json()
        except Exception as exc:
            logger.error("Bunker fuel price fetch failed: %s", exc)
            return []

        if not isinstance(records, list):
            logger.warning("Bunker fuel API returned unexpected format")
            return []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            date_str = rec.get("day", "")
            try:
                ts = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            # Determine which fuel columns to include
            if fuel_type == "all":
                fuels_to_check = FUEL_COLUMNS.items()
            else:
                col = FUEL_COLUMNS.get(fuel_type)
                if col:
                    fuels_to_check = [(fuel_type, col)]
                else:
                    fuels_to_check = FUEL_COLUMNS.items()

            for fuel_code, col_name in fuels_to_check:
                price_str = rec.get(col_name)
                if not price_str:
                    continue

                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"bunker-{fuel_code}-{date_str[:10]}",
                    "source_name": "USDA Bunker Fuel Prices",
                    "quality_score": 0.90,
                    "payload": {
                        "fuel_type": fuel_code,
                        "fuel_name": FUEL_NAMES.get(fuel_code, fuel_code),
                        "price_usd_mt": price,
                        "date": str(date_str)[:10],
                    },
                })

        logger.info("Bunker fuel prices returned %d observations", len(observations))
        return observations
