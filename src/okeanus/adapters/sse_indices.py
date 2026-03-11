"""Shanghai Shipping Exchange (SSE) container freight indices adapter.

CCFI (China Containerized Freight Index) since 1998 and
SCFI (Shanghai Containerized Freight Index) since 2009 — weekly.

Data: Published at en.sse.net.cn.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://en.sse.net.cn"
API_URL = f"{BASE_URL}/api/indices"

# Key shipping indices
INDICES = {
    "CCFI": "China Containerized Freight Index (composite)",
    "CCFI_EUR": "CCFI Europe route",
    "CCFI_USWC": "CCFI US West Coast route",
    "CCFI_USEC": "CCFI US East Coast route",
    "CCFI_JPN": "CCFI Japan route",
    "CCFI_KOR": "CCFI Korea route",
    "CCFI_SEA": "CCFI Southeast Asia route",
    "SCFI": "Shanghai Containerized Freight Index (composite)",
    "SCFI_EUR": "SCFI Europe route",
    "SCFI_USWC": "SCFI US West Coast route",
    "SCFI_MED": "SCFI Mediterranean route",
    "CBFI": "China Bulk Freight Index",
    "CTFI": "China Tanker Freight Index",
}


class SseIndicesAdapter(BaseAdapter):
    """Connector for Shanghai Shipping Exchange indices (no auth required).

    Returns CCFI, SCFI, CBFI, and CTFI freight indices — key benchmarks
    for China/Asia container and bulk shipping rates.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "sse_indices"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch SSE container/bulk freight indices.

        Extra params:
            index: index code (default: 'CCFI' — composite)
            route: specific trade route filter
            limit: max records (default: 200)
        """
        index_code = params.get("index", "CCFI")
        limit = params.get("limit", 200)

        year_start = time_start.year
        year_end = time_end.year

        # Try API endpoint
        url = f"{API_URL}/{index_code.lower()}"
        query: dict[str, Any] = {
            "startDate": time_start.strftime("%Y-%m-%d"),
            "endDate": time_end.strftime("%Y-%m-%d"),
            "format": "json",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("SSE API failed: %s, trying data page", exc)
            return await self._fetch_data_page(index_code, time_start, time_end, limit)

        records = data if isinstance(data, list) else data.get("data", data.get("indices", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            date_str = rec.get("date") or rec.get("Date") or rec.get("publishDate")
            value = rec.get("value") or rec.get("index") or rec.get("compositeIndex")

            if value is None or date_str is None:
                continue

            try:
                val = float(value)
                # Try multiple date formats
                for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
                    try:
                        ts = datetime.strptime(str(date_str)[:10], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [121.47, 31.23]},
                "source_id": f"sse-{index_code}-{date_str}",
                "source_name": "Shanghai Shipping Exchange",
                "quality_score": 0.95,
                "payload": {
                    "index_code": index_code,
                    "index_name": INDICES.get(index_code, index_code),
                    "date": str(date_str)[:10],
                    "value": val,
                    "change": rec.get("change") or rec.get("weeklyChange"),
                    "change_pct": rec.get("changePct") or rec.get("weeklyChangePct"),
                },
            })

        logger.info("SSE %s returned %d index values", index_code, len(observations))
        return observations

    async def _fetch_data_page(
        self,
        index_code: str,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: fetch from SSE data publishing page."""
        url = f"{BASE_URL}/indices/{index_code.lower()}/data"
        query = {
            "startDate": time_start.strftime("%Y-%m-%d"),
            "endDate": time_end.strftime("%Y-%m-%d"),
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("SSE data page fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("rows", [])
        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [121.47, 31.23]},
                "source_id": f"sse-page-{index_code}-{len(observations)}",
                "source_name": "Shanghai Shipping Exchange",
                "quality_score": 0.85,
                "payload": {
                    "index_code": index_code,
                    "raw": rec,
                },
            })

        return observations
