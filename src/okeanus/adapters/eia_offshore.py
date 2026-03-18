"""EIA Offshore Energy adapter — US offshore oil/gas/wind production data.

The US Energy Information Administration provides detailed offshore energy
production statistics via a free REST API (key required, free registration).

API docs: https://www.eia.gov/opendata/documentation.php
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.eia.gov/v2"

# Key offshore production series
OFFSHORE_ROUTES = {
    "crude_production": "/petroleum/crd/crpdn",
    "natural_gas": "/natural-gas/prod/sum",
}


class EiaOffshoreAdapter(BaseAdapter):
    """Connector for EIA offshore energy production data (free API key)."""

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)
        self._api_key = api_key or os.environ.get("EIA_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "eia_offshore"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """Fetch US offshore energy production data from EIA.

        Works without an API key using the preview endpoint (limited).

        Extra params:
            limit: Max records (default 100)
            series: 'crude_production' or 'natural_gas'
        """
        limit = params.get("limit", 100)

        # Use the petroleum summary endpoint (works without key)
        url = f"{BASE_URL}/petroleum/crd/crpdn/data/"
        start_str = time_start.strftime("%Y-%m")
        end_str = time_end.strftime("%Y-%m")

        query_params: dict[str, Any] = {
            "frequency": "monthly",
            "data[0]": "value",
            "facets[duoarea][]": "R3FM",  # Federal Offshore--Gulf of America
            "start": start_str,
            "end": end_str,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": min(limit, 5000),
        }
        if self._api_key:
            query_params["api_key"] = self._api_key

        try:
            resp = await self._request("GET", url, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("EIA Offshore fetch failed: %s", exc)
            return []

        response_data = data.get("response", data)
        records = response_data.get("data", [])
        if not isinstance(records, list):
            return []

        observations: list[dict[str, Any]] = []
        for rec in records:
            if len(observations) >= limit:
                break

            period = rec.get("period", "")
            value = rec.get("value")
            if value is None:
                continue

            try:
                value = float(value)
            except (ValueError, TypeError):
                continue

            # Parse period (YYYY-MM format)
            try:
                ts = datetime.strptime(str(period)[:7], "%Y-%m").replace(
                    day=1, tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                continue

            area = rec.get("area-name", rec.get("duoarea", ""))
            product = rec.get("product-name", rec.get("product", ""))
            units = rec.get("units", rec.get("unit", ""))

            observations.append({
                "obs_type": "energy_production",
                "timestamp": ts,
                "geometry": None,
                "source_id": f"eia-offshore-{period}-{rec.get('series', '')}",
                "source_name": "EIA",
                "quality_score": 1.0,
                "payload": {
                    "period": period,
                    "area": area,
                    "product": product,
                    "value": value,
                    "units": units,
                    "series_id": rec.get("series", ""),
                },
            })

        logger.info("EIA Offshore returned %d production records", len(observations))
        return observations
