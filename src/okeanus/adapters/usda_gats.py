"""USDA GATS (Global Agricultural Trade System) adapter.

Global seafood trade data since 1967 -- imports, exports by
country pair, HS code, value (USD), and quantity.

API: REST at apps.fas.usda.gov/OpenData/api/gats
Swagger: https://apps.fas.usda.gov/opendata/swagger/ui/index
Free API key required (obtain from https://api.data.gov/).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://apps.fas.usda.gov/OpenData/api/gats"

# HS Chapter 03 = Fish/crustaceans/molluscs + Chapter 16 = preserved fish
SEAFOOD_HS_CHAPTERS = ["03", "16"]

# Endpoint mapping: flow name -> GATS API path segment
FLOW_ENDPOINTS = {
    "exports": "censusExports",
    "imports": "censusImports",
    "reexports": "censusReExports",
}


class UsdaGatsAdapter(BaseAdapter):
    """Connector for USDA GATS -- global seafood trade (free key required).

    Returns bilateral trade flows for seafood products with value in
    USD and quantity, by HS code and country pair.

    The GATS API requires path parameters: partnerCode, year, month.
    API key is passed via the ``API_KEY`` header.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, max_retries=1, **kwargs)
        self._api_key = api_key or os.environ.get("USDA_GATS_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "usda_gats"

    @property
    def source_url(self) -> str:
        return "https://apps.fas.usda.gov/gats/default.aspx"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key:
            return {"API_KEY": self._api_key}
        return {}

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch USDA GATS seafood trade data.

        The GATS API requires partnerCode, year, and month as path
        parameters. This adapter queries the most recent month by
        default, or iterates over the requested time range.

        Extra params:
            partner: partner country code (default: 'MX')
            flow: 'imports', 'exports', or 'reexports' (default: 'exports')
            limit: max records (default: 500)
        """
        if not self._api_key:
            logger.warning("USDA GATS adapter requires api_key (obtain from api.data.gov)")
            return []

        partner = params.get("partner", "MX")
        flow = params.get("flow", "exports")
        limit = params.get("limit", 500)

        endpoint = FLOW_ENDPOINTS.get(flow, "censusExports")

        # Build list of (year, month) pairs to query
        months_to_query: list[tuple[int, int]] = []
        y, m = time_end.year, time_end.month
        while (y, m) >= (time_start.year, time_start.month):
            months_to_query.append((y, m))
            if len(months_to_query) >= 12:
                break
            m -= 1
            if m < 1:
                m = 12
                y -= 1

        observations: list[dict[str, Any]] = []
        consecutive_failures = 0

        for year, month in months_to_query:
            if len(observations) >= limit:
                break

            # If the API is consistently failing, stop early
            if consecutive_failures >= 2:
                logger.warning("USDA GATS: %d consecutive failures, stopping early (API may be down)", consecutive_failures)
                break

            month_str = f"{month:02d}"
            url = (
                f"{BASE_URL}/{endpoint}"
                f"/partnerCode/{partner}"
                f"/year/{year}"
                f"/month/{month_str}"
            )

            try:
                resp = await self._request(
                    "GET", url, headers=self._auth_headers(),
                )
                data = resp.json()
                consecutive_failures = 0
            except Exception as exc:
                logger.error("USDA GATS fetch failed for %d/%s: %s", year, month_str, exc)
                consecutive_failures += 1
                continue

            records = data if isinstance(data, list) else data.get("data", data.get("results", []))
            if not isinstance(records, list):
                continue

            for rec in records:
                if len(observations) >= limit:
                    break

                if not isinstance(rec, dict):
                    continue

                value = rec.get("value") or rec.get("Value") or rec.get("amount")
                if value is None:
                    continue

                try:
                    val = float(value)
                except (ValueError, TypeError):
                    continue

                rec_year = rec.get("year") or rec.get("Year") or year
                rec_month = rec.get("month") or rec.get("Month") or month

                try:
                    ts = datetime(int(rec_year), int(rec_month), 1)
                except (ValueError, TypeError):
                    ts = datetime(year, month, 1)

                partner_name = rec.get("partnerDescription") or rec.get("partner", partner)
                commodity = rec.get("commodityDescription") or rec.get("commodity", "")
                hs_code = rec.get("commodityCode") or rec.get("hs10Code", "")

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"gats-{flow}-{hs_code}-{partner_name}-{rec_year}-{rec_month}",
                    "source_name": "USDA GATS",
                    "quality_score": 0.95,
                    "payload": {
                        "flow": flow,
                        "hs_code": hs_code,
                        "commodity": commodity,
                        "partner_code": rec.get("partnerCode", partner),
                        "partner_name": partner_name,
                        "value_usd": val,
                        "quantity": rec.get("quantity") or rec.get("Quantity"),
                        "unit": rec.get("unitDescription", ""),
                        "year": int(rec_year),
                        "month": int(rec_month),
                    },
                })

        logger.info("USDA GATS returned %d trade records", len(observations))
        return observations
