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
# Real API discovered from JSP page source: /currentIndex?indexName=<code>
CURRENT_INDEX_URL = f"{BASE_URL}/currentIndex"

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

        # /currentIndex returns current + previous week for any index
        # Map user-facing codes to SSE's indexName parameter
        index_name_map = {
            "CCFI": "ccfi", "SCFI": "scfi", "CBFI": "cbfi",
            "CTFI": "ctfi", "CDFI": "cdfi",
        }
        sse_name = index_name_map.get(index_code.upper(), index_code.lower())

        try:
            resp = await self._request(
                "GET", CURRENT_INDEX_URL, params={"indexName": sse_name},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("SSE %s fetch failed: %s", index_code, exc)
            return []

        result = data.get("data", {})
        if not result:
            return []

        current_date = result.get("currentDate", "")
        last_date = result.get("lastDate", "")
        line_data = result.get("lineDataList", [])

        observations: list[dict[str, Any]] = []

        for line in line_data:
            props = line.get("properties", {})
            name_en = props.get("lineName_EN", "")
            current_val = line.get("currentContent")
            last_val = line.get("lastContent")
            pct = line.get("percentage")
            item_type = line.get("dataItemTypeName", "")

            if current_val is not None:
                try:
                    ts = datetime.strptime(current_date, "%Y-%m-%d")
                except (ValueError, TypeError):
                    ts = datetime.now()

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [121.47, 31.23]},
                    "source_id": f"sse-{item_type}-{current_date}",
                    "source_name": "Shanghai Shipping Exchange",
                    "quality_score": 0.95,
                    "payload": {
                        "index_code": index_code.upper(),
                        "index_name": INDICES.get(index_code.upper(), index_code),
                        "route": name_en,
                        "item_type": item_type,
                        "date": current_date,
                        "value": float(current_val),
                        "previous_value": float(last_val) if last_val is not None else None,
                        "previous_date": last_date,
                        "change_pct": float(pct) if pct is not None else None,
                        "unit": props.get("unit_EN", ""),
                    },
                })

        logger.info("SSE %s returned %d index values", index_code, len(observations))
        return observations
