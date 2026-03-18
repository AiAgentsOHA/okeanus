"""Regulations.gov adapter — US federal regulatory dockets (USCG, NOAA, BOEM).

Provides access to proposed rules, final rules, and public comments for
maritime/ocean regulatory agencies. Free API key required.

API docs: https://open.gsa.gov/api/regulationsgov/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.regulations.gov/v4"

# Maritime/ocean agency IDs
MARITIME_AGENCIES = [
    "USCG",   # US Coast Guard
    "NOAA",   # National Oceanic and Atmospheric Administration
    "BOEM",   # Bureau of Ocean Energy Management
    "BSEE",   # Bureau of Safety and Environmental Enforcement
    "MARAD",  # Maritime Administration
    "EPA",    # Environmental Protection Agency (ocean-related)
    "NMFS",   # National Marine Fisheries Service
    "FWS",    # Fish and Wildlife Service
]


class RegulationsGovAdapter(BaseAdapter):
    """Connector for Regulations.gov federal rulemaking API."""

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)
        self._api_key = api_key or os.environ.get("REGULATIONS_GOV_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "regulations_gov"

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
        """Fetch regulatory documents from maritime agencies.

        Extra params:
            agencies: List of agency codes (default: MARITIME_AGENCIES)
            search: Text search term
            doc_type: 'Rule', 'Proposed Rule', 'Notice' (default all)
            limit: Max records (default 25)
        """
        if not self._api_key:
            logger.warning("Regulations.gov requires an API key (free at api.data.gov)")
            return []

        limit = params.get("limit", 25)
        agencies = params.get("agencies", MARITIME_AGENCIES)
        search = params.get("search", "")
        doc_type = params.get("doc_type", "")

        start_str = time_start.strftime("%Y-%m-%d")
        end_str = time_end.strftime("%Y-%m-%d")

        headers = {"X-Api-Key": self._api_key}

        all_observations: list[dict[str, Any]] = []

        for agency in agencies[:4]:  # Limit agencies per call
            query_params: dict[str, Any] = {
                "filter[agencyId]": agency,
                "filter[postedDate][ge]": start_str,
                "filter[postedDate][le]": end_str,
                "page[size]": min(limit, 25),
                "sort": "-postedDate",
            }
            if search:
                query_params["filter[searchTerm]"] = search
            if doc_type:
                query_params["filter[documentType]"] = doc_type

            try:
                resp = await self._request(
                    "GET",
                    f"{BASE_URL}/documents",
                    params=query_params,
                    headers=headers,
                )
                data = resp.json()
            except Exception as exc:
                logger.error("Regulations.gov fetch failed for %s: %s", agency, exc)
                continue

            for doc in data.get("data", []):
                attrs = doc.get("attributes", {})
                doc_id = doc.get("id", "")
                title = attrs.get("title", "")
                posted = attrs.get("postedDate", "")
                doc_type_val = attrs.get("documentType", "")

                ts = _parse_date(posted)
                if ts is None:
                    ts = datetime.now(timezone.utc)

                all_observations.append({
                    "obs_type": "regulation",
                    "timestamp": ts,
                    "geometry": None,
                    "source_id": f"regsgov-{doc_id}",
                    "source_name": "Regulations.gov",
                    "quality_score": 1.0,
                    "payload": {
                        "document_id": doc_id,
                        "title": title,
                        "agency": agency,
                        "document_type": doc_type_val,
                        "posted_date": posted,
                        "docket_id": attrs.get("docketId", ""),
                        "comment_count": attrs.get("numberOfCommentsReceived"),
                        "url": f"https://www.regulations.gov/document/{doc_id}",
                    },
                })

        all_observations.sort(key=lambda x: x["timestamp"], reverse=True)
        logger.info("Regulations.gov returned %d documents", len(all_observations))
        return all_observations[:limit]


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
