"""USDA GATS (Global Agricultural Trade System) adapter.

Global seafood trade data since 1967 — imports, exports by
country pair, HS code, value (USD), and quantity.

API: REST at apps.fas.usda.gov.
Free API key required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://apps.fas.usda.gov/OpenData/api/esd"

# HS Chapter 03 = Fish/crustaceans/molluscs + Chapter 16 = preserved fish
SEAFOOD_HS_CHAPTERS = ["03", "16"]


class UsdaGatsAdapter(BaseAdapter):
    """Connector for USDA GATS — global seafood trade (free key required).

    Returns bilateral trade flows for seafood products with value in
    USD and quantity, by HS code and country pair.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_key = api_key

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

        Extra params:
            hs_code: HS code chapter or full code (default: '03')
            partner: partner country code
            flow: 'imports' or 'exports' (default: 'exports')
            limit: max records (default: 500)
        """
        if not self._api_key:
            logger.warning("USDA GATS adapter requires api_key (free at apps.fas.usda.gov)")
            return []

        hs_code = params.get("hs_code", "03")
        partner = params.get("partner")
        flow = params.get("flow", "exports")
        limit = params.get("limit", 500)

        year_start = time_start.year
        year_end = time_end.year

        url = f"{BASE_URL}/{flow}"
        query: dict[str, Any] = {
            "commodityCode": hs_code,
            "marketYear": year_end,
        }
        if partner:
            query["partnerCode"] = partner

        try:
            resp = await self._request(
                "GET", url, params=query, headers=self._auth_headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("USDA GATS fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            year = rec.get("marketYear") or rec.get("year")
            month = rec.get("month") or rec.get("Month") or 1
            value = rec.get("value") or rec.get("Value") or rec.get("amount")

            if value is None:
                continue

            try:
                ts = datetime(int(year), int(month), 1)
                val = float(value)
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            partner_name = rec.get("partnerDescription") or rec.get("partner", "")
            commodity = rec.get("commodityDescription") or rec.get("commodity", "")

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"gats-{flow}-{hs_code}-{partner_name}-{year}-{month}",
                "source_name": "USDA GATS",
                "quality_score": 0.95,
                "payload": {
                    "flow": flow,
                    "hs_code": hs_code,
                    "commodity": commodity,
                    "partner_code": rec.get("partnerCode", ""),
                    "partner_name": partner_name,
                    "value_usd": val,
                    "quantity": rec.get("quantity") or rec.get("Quantity"),
                    "unit": rec.get("unitDescription", ""),
                    "year": int(year),
                    "month": int(month),
                },
            })

        logger.info("USDA GATS returned %d trade records", len(observations))
        return observations
