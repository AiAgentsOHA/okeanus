"""IUU Fishing Index adapter — country compliance rankings.

IUU (Illegal, Unreported and Unregulated) fishing risk scores
for coastal, flag, port, and market states based on 40 indicators.

Data: Poseidon Aquatic Resource Management / NOAA / Global Initiative.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://iuufishingindex.net/api/v1"
RANKINGS_URL = f"{BASE_URL}/rankings"


class IuuIndexAdapter(BaseAdapter):
    """Connector for IUU Fishing Index — country compliance (no auth).

    Returns IUU fishing risk scores and rankings for countries as
    coastal, flag, port, and market states.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "iuu_index"

    @property
    def source_url(self) -> str:
        return "https://iuufishingindex.net/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch IUU Fishing Index country rankings.

        Extra params:
            country: ISO3 country code
            state_type: 'overall', 'coastal', 'flag', 'port', 'market'
            limit: max records (default: 200)
        """
        country = params.get("country")
        state_type = params.get("state_type", "overall")
        limit = params.get("limit", 200)

        query: dict[str, Any] = {
            "type": state_type,
            "limit": limit,
            "format": "json",
        }
        if country:
            query["country"] = country

        try:
            resp = await self._request("GET", RANKINGS_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("IUU Index fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("rankings", data.get("countries", data.get("data", [])))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            country_name = rec.get("country") or rec.get("Country") or rec.get("name", "")
            country_code = rec.get("iso3") or rec.get("ISO3") or rec.get("country_code", "")
            score = rec.get("score") or rec.get("Score") or rec.get("overall_score")
            rank = rec.get("rank") or rec.get("Rank") or rec.get("position")

            year = rec.get("year") or rec.get("Year") or time_end.year
            try:
                ts = datetime(int(year), 1, 1)
            except (ValueError, TypeError):
                ts = datetime.now()

            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"iuu-idx-{country_code}-{state_type}-{year}",
                "source_name": "IUU Fishing Index",
                "quality_score": 0.90,
                "payload": {
                    "country_name": country_name,
                    "country_code": country_code,
                    "state_type": state_type,
                    "overall_score": score,
                    "rank": rank,
                    "coastal_score": rec.get("coastal_score") or rec.get("Coastal"),
                    "flag_score": rec.get("flag_score") or rec.get("Flag"),
                    "port_score": rec.get("port_score") or rec.get("Port"),
                    "market_score": rec.get("market_score") or rec.get("Market"),
                    "year": int(year),
                    "vulnerability": rec.get("vulnerability"),
                    "prevalence": rec.get("prevalence"),
                    "response": rec.get("response"),
                },
            })

        logger.info("IUU Index returned %d country scores", len(observations))
        return observations
