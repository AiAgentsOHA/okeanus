"""Bunker Index adapter — marine fuel price indices.

VLSFO, HSFO, IFO380, MDO, and MGO indices since 2009.

Data: bunkerindex.com (publicly available indices).
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.bunkerindex.com"
API_URL = f"{BASE_URL}/api/v1"

# Fuel types tracked
FUEL_TYPES = {
    "VLSFO": "Very Low Sulphur Fuel Oil (0.5% S)",
    "HSFO": "High Sulphur Fuel Oil (3.5% S)",
    "IFO380": "Intermediate Fuel Oil 380cSt",
    "MDO": "Marine Diesel Oil",
    "MGO": "Marine Gas Oil",
    "LSMGO": "Low Sulphur Marine Gas Oil",
}

# Key bunkering ports
PORTS = [
    "Singapore", "Rotterdam", "Fujairah", "Houston",
    "Shanghai", "Busan", "Gibraltar", "Piraeus",
    "Panama", "Los Angeles", "New York", "Hong Kong",
]


class BunkerIndexAdapter(BaseAdapter):
    """Connector for Bunker Index — marine fuel prices (no auth required).

    Returns daily VLSFO/HSFO/MGO/MDO indices and port-specific
    bunker fuel prices.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "bunker_index"

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
        """Fetch bunker fuel price indices.

        Extra params:
            fuel_type: fuel code (default: 'VLSFO')
            port: bunkering port name
            limit: max records (default: 200)
        """
        fuel_type = params.get("fuel_type", "VLSFO")
        port = params.get("port")
        limit = params.get("limit", 200)

        # Try API
        url = f"{API_URL}/prices"
        query: dict[str, Any] = {
            "fuel": fuel_type,
            "startDate": time_start.strftime("%Y-%m-%d"),
            "endDate": time_end.strftime("%Y-%m-%d"),
            "format": "json",
        }
        if port:
            query["port"] = port

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("Bunker Index API failed: %s, trying index page", exc)
            return await self._fetch_index_page(fuel_type, time_start, time_end, limit)

        records = data if isinstance(data, list) else data.get("prices", data.get("data", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            date_str = rec.get("date") or rec.get("Date")
            price = rec.get("price") or rec.get("Price") or rec.get("value")

            if price is None or date_str is None:
                continue

            try:
                val = float(price)
                ts = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            port_name = rec.get("port") or rec.get("Port") or port or "Global"

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"bunker-{fuel_type}-{port_name}-{date_str}",
                "source_name": "Bunker Index",
                "quality_score": 0.90,
                "payload": {
                    "fuel_type": fuel_type,
                    "fuel_name": FUEL_TYPES.get(fuel_type, fuel_type),
                    "port": port_name,
                    "price_usd_mt": val,
                    "date": str(date_str)[:10],
                    "change": rec.get("change"),
                    "change_pct": rec.get("changePct"),
                },
            })

        logger.info("Bunker Index %s returned %d prices", fuel_type, len(observations))
        return observations

    async def _fetch_index_page(
        self,
        fuel_type: str,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: fetch from index data page."""
        url = f"{BASE_URL}/data/{fuel_type.lower()}"

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("Bunker Index page fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("index", data.get("history", []))
        if not isinstance(records, list):
            return []

        observations: list[dict[str, Any]] = []
        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue
            observations.append({
                "obs_type": "economic",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"bunker-page-{fuel_type}-{len(observations)}",
                "source_name": "Bunker Index",
                "quality_score": 0.80,
                "payload": {"fuel_type": fuel_type, "raw": rec},
            })

        return observations
