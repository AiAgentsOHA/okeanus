"""Green Climate Fund (GCF) adapter — ocean/coastal climate projects.

300+ projects with full financial data, including coastal zone
management, marine ecosystem restoration, and climate adaptation.

API: REST at api-portal.gcfund.org.
Free registration required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.greenclimate.fund/v1"
PROJECTS_URL = f"{BASE_URL}/projects"


class GcfOceanAdapter(BaseAdapter):
    """Connector for Green Climate Fund — ocean/coastal projects (free reg).

    Returns GCF-funded projects related to ocean, coastal, marine,
    and fisheries with full financial breakdowns.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        return "gcf_ocean"

    @property
    def source_url(self) -> str:
        return "https://www.greenclimate.fund/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch GCF ocean/coastal climate projects.

        Extra params:
            query: search text (default: 'ocean OR marine OR coastal')
            country: ISO3 country code
            status: project status filter
            limit: max records (default: 100)
        """
        query = params.get("query", "ocean OR marine OR coastal OR fisheries")
        country = params.get("country")
        status = params.get("status")
        limit = params.get("limit", 100)

        query_params: dict[str, Any] = {
            "q": query,
            "limit": limit,
        }
        if country:
            query_params["country"] = country
        if status:
            query_params["status"] = status

        try:
            resp = await self._request(
                "GET", PROJECTS_URL,
                params=query_params, headers=self._headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("GCF fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("projects", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            project_id = rec.get("id") or rec.get("projectId") or rec.get("ref", "")
            title = rec.get("title") or rec.get("name") or ""
            approval_date = rec.get("approvalDate") or rec.get("approval_date") or ""

            try:
                ts = datetime.strptime(approval_date[:10], "%Y-%m-%d") if approval_date else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            if ts < time_start or ts > time_end:
                continue

            gcf_amount = rec.get("gcfAmount") or rec.get("gcf_amount") or rec.get("financing")
            co_financing = rec.get("coFinancing") or rec.get("co_financing")

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"gcf-{project_id}",
                "source_name": "Green Climate Fund",
                "quality_score": 0.95,
                "payload": {
                    "project_id": str(project_id),
                    "title": title,
                    "country": rec.get("country") or rec.get("countries", ""),
                    "gcf_amount_usd": gcf_amount,
                    "co_financing_usd": co_financing,
                    "total_financing": rec.get("totalFinancing") or rec.get("total"),
                    "sector": rec.get("sector") or rec.get("theme", ""),
                    "status": rec.get("status", ""),
                    "entity": rec.get("accreditedEntity") or rec.get("entity", ""),
                    "approval_date": approval_date,
                    "result_areas": rec.get("resultAreas", []),
                },
            })

        logger.info("GCF returned %d ocean/coastal projects", len(observations))
        return observations
