"""OilPriceAPI adapter — marine fuel prices every 15 minutes.

MGO, VLSFO, HFO prices from 8 major bunkering hubs with
a free tier available.

API: REST at api.oilpriceapi.com.
Free tier: 100 requests/day. Requires Bearer token.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.oilpriceapi.com/v1"

# Marine fuel product codes
PRODUCTS = {
    "MGO_RDAM": "Marine Gas Oil, Rotterdam",
    "VLSFO_SING": "VLSFO 0.5%, Singapore",
    "VLSFO_RDAM": "VLSFO 0.5%, Rotterdam",
    "VLSFO_HOUST": "VLSFO 0.5%, Houston",
    "HFO_SING": "HFO 380cSt, Singapore",
    "HFO_RDAM": "HFO 380cSt, Rotterdam",
    "MGO_SING": "Marine Gas Oil, Singapore",
    "BRENT": "Brent Crude (reference)",
    "WTI": "WTI Crude (reference)",
}


class OilPriceApiAdapter(BaseAdapter):
    """Connector for OilPriceAPI — marine fuel prices (free tier available).

    Returns intraday VLSFO/MGO/HFO prices from major bunkering hubs,
    updated every 15 minutes.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        return "oilprice_api"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "15-minute"

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key:
            return {
                "Authorization": f"Token {self._api_key}",
                "Content-Type": "application/json",
            }
        return {}

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch marine fuel prices from OilPriceAPI.

        Extra params:
            product: fuel product code (default: fetch latest for all)
            endpoint: 'latest' or 'past_day' (default: 'latest')
        """
        if not self._api_key:
            logger.warning(
                "OilPriceAPI requires api_key (free tier at oilpriceapi.com)",
            )
            return []

        endpoint = params.get("endpoint", "latest")
        product = params.get("product")

        if endpoint == "past_day":
            return await self._fetch_past_day(product)

        return await self._fetch_latest(product)

    async def _fetch_latest(self, product: str | None) -> list[dict[str, Any]]:
        """Fetch latest price snapshot."""
        url = f"{BASE_URL}/prices/latest"

        try:
            resp = await self._request(
                "GET", url, headers=self._auth_headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("OilPriceAPI latest fetch failed: %s", exc)
            return []

        prices = data.get("data", {})
        if isinstance(prices, dict):
            prices = [prices]
        elif not isinstance(prices, list):
            prices = []

        observations: list[dict[str, Any]] = []

        for price_data in prices:
            if not isinstance(price_data, dict):
                continue

            price = price_data.get("price")
            code = price_data.get("code") or price_data.get("product", "")
            ts_str = price_data.get("created_at") or price_data.get("timestamp", "")

            if price is None:
                continue

            if product and product.upper() != code.upper():
                continue

            try:
                val = float(price)
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()
                val = float(price)

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"oilprice-{code}-{ts.strftime('%Y%m%d%H%M')}",
                "source_name": "OilPriceAPI",
                "quality_score": 0.90,
                "payload": {
                    "product_code": code,
                    "product_name": PRODUCTS.get(code, code),
                    "price_usd": val,
                    "currency": price_data.get("currency", "USD"),
                    "unit": price_data.get("unit", "per barrel"),
                    "formatted": price_data.get("formatted", ""),
                },
            })

        logger.info("OilPriceAPI returned %d latest prices", len(observations))
        return observations

    async def _fetch_past_day(self, product: str | None) -> list[dict[str, Any]]:
        """Fetch past 24h prices (intraday)."""
        url = f"{BASE_URL}/prices/past_day"

        try:
            resp = await self._request(
                "GET", url, headers=self._auth_headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("OilPriceAPI past_day fetch failed: %s", exc)
            return []

        prices = data.get("data", {}).get("prices", [])
        if not isinstance(prices, list):
            prices = []

        observations: list[dict[str, Any]] = []

        for price_data in prices:
            if not isinstance(price_data, dict):
                continue

            price = price_data.get("price")
            code = price_data.get("code") or ""
            ts_str = price_data.get("created_at", "")

            if price is None:
                continue
            if product and product.upper() != code.upper():
                continue

            try:
                val = float(price)
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now()
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"oilprice-{code}-{ts.strftime('%Y%m%d%H%M')}",
                "source_name": "OilPriceAPI",
                "quality_score": 0.90,
                "payload": {
                    "product_code": code,
                    "product_name": PRODUCTS.get(code, code),
                    "price_usd": val,
                },
            })

        logger.info("OilPriceAPI past_day returned %d prices", len(observations))
        return observations
