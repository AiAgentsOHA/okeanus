"""eCFR adapter — US Code of Federal Regulations maritime titles.

Searches Title 33 (Navigation and Navigable Waters) and Title 46 (Shipping)
for maritime regulatory text. No auth required.

API docs: https://www.ecfr.gov/reader-aids/ecfr-developer-resources
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.ecfr.gov/api/search/v1/results"
VERSIONS_URL = "https://www.ecfr.gov/api/versioner/v1/versions/title-{title}"
TITLES_URL = "https://www.ecfr.gov/api/versioner/v1/titles"

# Maritime-relevant CFR titles
MARITIME_TITLES = [33, 46]

# Default maritime search terms
DEFAULT_QUERIES = [
    "vessel safety",
    "marine pollution",
    "offshore drilling",
    "fisheries management",
    "port security",
    "navigation rules",
]


class EcfrAdapter(BaseAdapter):
    """Connector for the Electronic Code of Federal Regulations (maritime)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.5, **kwargs)

    @property
    def source_name(self) -> str:
        return "ecfr"

    @property
    def source_url(self) -> str:
        return "https://www.ecfr.gov/"

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
        """Search maritime CFR sections by keyword.

        Extra params:
            query: Search term (default: 'vessel safety')
            title: CFR title number (default: searches 33 and 46)
            per_page: Results per page (default 20, max 20)
            limit: Max total records (default 50)
        """
        limit = params.get("limit", 50)
        query = params.get("query", "vessel safety")
        titles = params.get("title", MARITIME_TITLES)
        per_page = min(params.get("per_page", 20), 20)

        if isinstance(titles, int):
            titles = [titles]

        modified_after = time_start.strftime("%Y-%m-%d")

        observations: list[dict[str, Any]] = []

        for title in titles:
            if len(observations) >= limit:
                break

            query_params: dict[str, Any] = {
                "query": query,
                "hierarchy[title]": str(title),
                "per_page": per_page,
                "page": 1,
                "order": "relevance",
            }

            try:
                resp = await self._request("GET", SEARCH_URL, params=query_params)
                data = resp.json()
            except Exception as exc:
                logger.error("eCFR search failed for title %d: %s", title, exc)
                continue

            results = data.get("results", [])
            for rec in results:
                if len(observations) >= limit:
                    break

                hierarchy = rec.get("hierarchy", {})
                headings = rec.get("hierarchy_headings", {})
                excerpt = rec.get("full_text_excerpt", "")
                rec_type = rec.get("type", "")
                starts_on = rec.get("starts_on", "")

                ts = _parse_date(starts_on) or datetime.now(timezone.utc)

                # Build a readable reference
                parts = []
                for level in ("title", "chapter", "part", "subpart", "section"):
                    val = hierarchy.get(level)
                    if val:
                        heading = headings.get(level, "")
                        parts.append(f"{level.capitalize()} {val}: {heading}" if heading else f"{level.capitalize()} {val}")

                ref = " > ".join(parts) if parts else f"Title {title}"

                observations.append({
                    "obs_type": "regulation",
                    "timestamp": ts,
                    "geometry": None,
                    "source_id": f"ecfr-{hierarchy.get('title','')}-{hierarchy.get('section',hierarchy.get('part',''))}",
                    "source_name": "eCFR",
                    "quality_score": 0.95,
                    "payload": {
                        "reference": ref,
                        "title_number": hierarchy.get("title", ""),
                        "chapter": hierarchy.get("chapter", ""),
                        "part": hierarchy.get("part", ""),
                        "section": hierarchy.get("section", ""),
                        "type": rec_type,
                        "excerpt": excerpt[:500] if excerpt else "",
                        "starts_on": starts_on,
                        "query": query,
                    },
                })

        logger.info("eCFR returned %d regulatory sections", len(observations))
        return observations


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
