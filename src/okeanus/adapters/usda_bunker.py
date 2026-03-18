"""USDA Socrata bunker fuel price adapter.

Daily bunker fuel prices from the USDA Agricultural Transportation
open data portal via SODA API.

API: SODA (Socrata Open Data API) at agtransport.usda.gov.
Free app token recommended but not required.

Dataset 4v3x-mj86: daily bunker fuel prices (VLSFO, MGO, IFO 380).
Columns: day, vlsfo_fuel_oil_imo_2020_grade_0_5, marine_gas_oil,
         intermdiate_fuel_oil_380cst, month, year.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://agtransport.usda.gov/resource"

# Fuel price columns in dataset 4v3x-mj86
FUEL_COLUMNS = {
    "vlsfo_fuel_oil_imo_2020_grade_0_5": "VLSFO (IMO 2020)",
    "marine_gas_oil": "Marine Gas Oil (MGO)",
    "intermdiate_fuel_oil_380cst": "IFO 380",
}


class UsdaBunkerAdapter(BaseAdapter):
    """Connector for USDA SODA API — daily bunker fuel prices (free).

    Returns daily marine fuel prices from USDA agricultural
    transportation monitoring, useful for vessel operating cost analysis.
    """

    def __init__(self, *, app_token: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._app_token = app_token

    @property
    def source_name(self) -> str:
        return "usda_bunker"

    @property
    def source_url(self) -> str:
        return "https://agtransport.usda.gov/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._app_token:
            headers["X-App-Token"] = self._app_token
        return headers

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch USDA bunker/transport fuel prices.

        Extra params:
            dataset_id: Socrata dataset 4-4 identifier (default: 4v3x-mj86)
            limit: max records (default: 1000)
        """
        dataset_id = params.get("dataset_id", "4v3x-mj86")
        limit = params.get("limit", 1000)

        url = f"{BASE_URL}/{dataset_id}.json"

        # Build SoQL query — date column is "day" in 4v3x-mj86
        start_str = time_start.strftime("%Y-%m-%dT00:00:00")
        end_str = time_end.strftime("%Y-%m-%dT23:59:59")

        query: dict[str, Any] = {
            "$where": f"day >= '{start_str}' AND day <= '{end_str}'",
            "$limit": limit,
            "$order": "day DESC",
        }

        try:
            resp = await self._request(
                "GET", url, params=query, headers=self._headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("USDA SODA fetch failed: %s", exc)
            return []

        if not isinstance(data, list):
            data = data.get("data", data.get("results", []))

        observations: list[dict[str, Any]] = []

        for rec in data:
            if not isinstance(rec, dict):
                continue

            date_str = rec.get("day")
            if not date_str:
                continue

            try:
                date_clean = str(date_str)[:10]
                ts = datetime.strptime(date_clean, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            # Emit one observation per fuel type per day
            for col, label in FUEL_COLUMNS.items():
                price_str = rec.get(col)
                if price_str is None:
                    continue
                try:
                    val = float(price_str)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
                    "source_id": f"usda-bunker-{col}-{date_clean}",
                    "source_name": "USDA AgTransport",
                    "quality_score": 0.90,
                    "payload": {
                        "fuel_type": label,
                        "price_usd_per_mt": val,
                        "date": date_clean,
                        "month": rec.get("month", ""),
                        "year": rec.get("year", ""),
                    },
                })

        logger.info("USDA bunker returned %d price records", len(observations))
        return observations
