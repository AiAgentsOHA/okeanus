"""USDA Socrata bunker fuel price adapter.

Daily bunker fuel prices from the USDA Agricultural Transportation
open data portal via SODA API.

API: SODA (Socrata Open Data API) at agtransport.usda.gov.
Free app token recommended but not required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://agtransport.usda.gov/resource"

# Known dataset identifiers for bunker/transportation fuel
DATASETS = {
    "bunker_fuel": "daily bunker fuel prices",
    "ocean_rates": "ocean freight rates for grains",
    "inland_barge": "inland barge freight rates",
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
            dataset_id: Socrata dataset 4-4 identifier
            fuel_type: filter by fuel type
            limit: max records (default: 1000)
        """
        dataset_id = params.get("dataset_id", "bxe3-k54q")
        fuel_type = params.get("fuel_type")
        limit = params.get("limit", 1000)

        url = f"{BASE_URL}/{dataset_id}.json"

        # Build SoQL query
        where_clauses = []
        start_str = time_start.strftime("%Y-%m-%dT00:00:00")
        end_str = time_end.strftime("%Y-%m-%dT23:59:59")
        where_clauses.append(f"date >= '{start_str}'")
        where_clauses.append(f"date <= '{end_str}'")

        if fuel_type:
            where_clauses.append(f"fuel_type = '{fuel_type}'")

        query: dict[str, Any] = {
            "$where": " AND ".join(where_clauses),
            "$limit": limit,
            "$order": "date DESC",
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

            # SODA returns various field naming conventions
            date_str = rec.get("date") or rec.get("Date") or rec.get("report_date")
            price = (
                rec.get("price") or rec.get("Price")
                or rec.get("bunker_price") or rec.get("value")
            )

            if price is None or date_str is None:
                continue

            try:
                val = float(price)
                # Handle ISO datetime or date-only
                date_clean = str(date_str)[:10]
                ts = datetime.strptime(date_clean, "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            ft = rec.get("fuel_type") or rec.get("product") or fuel_type or ""
            port = rec.get("port") or rec.get("location") or rec.get("hub") or ""

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [-98.5, 39.8]},
                "source_id": f"usda-bunker-{ft}-{port}-{date_clean}",
                "source_name": "USDA AgTransport",
                "quality_score": 0.90,
                "payload": {
                    "fuel_type": ft,
                    "port": port,
                    "price_usd": val,
                    "unit": rec.get("unit") or rec.get("units") or "USD/mt",
                    "date": date_clean,
                    "source_report": rec.get("source") or rec.get("report_name", ""),
                },
            })

        logger.info("USDA bunker returned %d price records", len(observations))
        return observations
