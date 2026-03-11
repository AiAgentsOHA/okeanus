"""World Benchmarking Alliance Seafood Stewardship Index adapter.

Rankings and scores for the 30 largest seafood companies globally
across governance, traceability, ecosystems, and social responsibility.

Data: Downloads at worldbenchmarkingalliance.org.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.worldbenchmarkingalliance.org/api/v1"
RANKINGS_URL = f"{BASE_URL}/rankings/seafood-stewardship-index"


class WbaSeafoodAdapter(BaseAdapter):
    """Connector for WBA Seafood Stewardship Index (no auth required).

    Returns sustainability rankings and scores for the world's 30
    largest seafood companies.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "wba_seafood"

    @property
    def source_url(self) -> str:
        return "https://www.worldbenchmarkingalliance.org/rankings/seafood-stewardship-index/"

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
        """Fetch WBA Seafood Stewardship Index rankings.

        Extra params:
            company: company name filter
            limit: max records (default: 30)
        """
        company = params.get("company")
        limit = params.get("limit", 30)

        query: dict[str, Any] = {"limit": limit, "format": "json"}
        if company:
            query["q"] = company

        try:
            resp = await self._request("GET", RANKINGS_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("WBA SSI fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("rankings", data.get("companies", data.get("data", [])))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            name = rec.get("company") or rec.get("name") or rec.get("company_name", "")
            rank = rec.get("rank") or rec.get("position")
            score = rec.get("score") or rec.get("total_score")

            year = rec.get("year") or time_end.year
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
                "source_id": f"wba-ssi-{name}-{year}",
                "source_name": "WBA Seafood Stewardship Index",
                "quality_score": 0.93,
                "payload": {
                    "company_name": name,
                    "rank": rank,
                    "total_score": score,
                    "governance_score": rec.get("governance") or rec.get("governance_score"),
                    "ecosystems_score": rec.get("ecosystems") or rec.get("ecosystems_score"),
                    "traceability_score": rec.get("traceability") or rec.get("traceability_score"),
                    "social_score": rec.get("social") or rec.get("social_responsibility_score"),
                    "country": rec.get("country") or rec.get("headquarters", ""),
                    "sector": rec.get("sector") or rec.get("industry", ""),
                    "revenue_usd": rec.get("revenue"),
                    "year": int(year),
                },
            })

        logger.info("WBA SSI returned %d company rankings", len(observations))
        return observations
