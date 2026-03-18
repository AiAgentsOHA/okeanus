"""Verra VCS blue carbon credits adapter via Verra Registry UI API.

Blue carbon project registrations from Verra's Verified Carbon Standard,
accessed through the public UI API at registry.verra.org/uiapi/.

The previous CAD Trust API (api.climateactiondata.org) returns 404 for
project searches. The Verra Registry UI API is used instead -- it is the
same API that powers the public search at registry.verra.org/app/search/.

API: POST to registry.verra.org/uiapi/resource/resource/search
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Verra Registry UI API -- powers the public search page, no auth needed.
VERRA_UI_API = "https://registry.verra.org/uiapi"

# Blue carbon methodology codes
BLUE_CARBON_METHODOLOGIES = [
    "VM0007",   # REDD+ Methodology Framework (mangroves)
    "VM0024",   # Methodology for Coastal Wetland Creation
    "VM0033",   # Methodology for Tidal Wetland Restoration
    "VM0036",   # Methodology for Rewetting Drained Temperate Peatlands (coastal)
]

BLUE_KEYWORDS = [
    "blue carbon",
    "mangrove",
    "seagrass",
    "tidal wetland",
    "coastal wetland",
    "salt marsh",
    "ocean",
    "marine",
]


class VerraBlueAdapter(BaseAdapter):
    """Connector for Verra VCS blue carbon projects (no auth).

    Uses the Verra Registry UI API at registry.verra.org to search
    for blue carbon projects. Returns project metadata including
    proponent, status, methodology, country, and estimated emission
    reductions.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "verra_blue"

    @property
    def source_url(self) -> str:
        return "https://registry.verra.org/app/search/VCS"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def _search_verra(
        self,
        keyword: str,
        limit: int,
        country: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search Verra Registry UI API for projects matching keyword."""
        url = (
            f"{VERRA_UI_API}/resource/resource/search"
            f"?maxResults={limit}&$count=true&$skip=0&$top={limit}"
        )
        body: dict[str, Any] = {
            "program": "VCS",
            "keywordSearch": keyword,
        }
        if country:
            body["country"] = country

        headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        resp = await self._request("POST", url, json=body, headers=headers)
        data = resp.json()

        records = data.get("value", [])
        if not isinstance(records, list):
            records = []
        return records

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch blue carbon project data from Verra Registry.

        Extra params:
            query: search term (default: 'mangrove')
            country: country name filter
            limit: max records (default: 200)
        """
        query = params.get("query", "mangrove")
        country = params.get("country")
        limit = params.get("limit", 200)

        # Search Verra Registry for blue carbon projects
        all_records: list[dict[str, Any]] = []
        search_terms = [query]

        # If using the default query, also search for other blue carbon terms
        if query == "mangrove":
            search_terms = ["mangrove", "seagrass", "blue carbon", "tidal wetland"]

        seen_ids: set[str] = set()
        for term in search_terms:
            if len(all_records) >= limit:
                break
            try:
                # Always request a full page (50) per term so the API
                # returns enough candidates before blue-carbon filtering.
                records = await self._search_verra(
                    term,
                    50,
                    country,
                )
                for rec in records:
                    rid = rec.get("resourceIdentifier", "")
                    if rid not in seen_ids:
                        seen_ids.add(rid)
                        all_records.append(rec)
            except Exception as exc:
                logger.warning("Verra search for '%s' failed: %s", term, exc)
                continue

        if not all_records:
            logger.error("Verra Registry search returned no results")
            return []

        observations: list[dict[str, Any]] = []

        for rec in all_records:
            if len(observations) >= limit:
                break
            if not isinstance(rec, dict):
                continue

            project_id = rec.get("resourceIdentifier", "")
            name = rec.get("resourceName", "")
            proponent = rec.get("proponent", "")
            country_name = rec.get("country", "")
            region = rec.get("region", "")
            status = rec.get("resourceStatus", "")
            protocols = rec.get("protocols", "")
            categories = rec.get("protocolCategories", "")
            sub_categories = rec.get("protocolSubCategories", "")
            est_annual_er = rec.get("estAnnualEmissionReductions")

            # Check if this is a blue carbon project
            name_lower = name.lower()
            cats_lower = (categories or "").lower() + " " + (sub_categories or "").lower()
            is_blue = any(
                kw in name_lower or kw in cats_lower
                for kw in BLUE_KEYWORDS
            )
            # Check methodology codes
            if protocols:
                for meth in BLUE_CARBON_METHODOLOGIES:
                    if meth in protocols:
                        is_blue = True
                        break
            # Also include WRC (Wetlands Restoration and Conservation) subcategory
            if sub_categories and "WRC" in sub_categories:
                is_blue = True

            if not is_blue and query == "mangrove":
                continue

            # Parse dates
            start_date = rec.get("creditingPeriodStartDate", "")
            reg_date = rec.get("projectRegistrationDate", "")
            create_date = rec.get("createDate", "")
            date_str = start_date or reg_date or create_date or ""
            try:
                ts = (
                    datetime.strptime(date_str[:10], "%Y-%m-%d")
                    if date_str
                    else datetime.now()
                )
            except (ValueError, TypeError):
                ts = datetime.now()

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [0.0, 0.0],
                },
                "source_id": f"verra-{project_id}",
                "source_name": "Verra VCS Registry",
                "quality_score": 0.93,
                "payload": {
                    "project_id": str(project_id),
                    "name": name,
                    "registry": "VCS",
                    "country": country_name,
                    "region": region,
                    "methodology": protocols,
                    "project_category": categories,
                    "project_subcategory": sub_categories or "",
                    "status": status,
                    "proponent": proponent,
                    "est_annual_emission_reductions": est_annual_er,
                    "crediting_period_start": start_date,
                    "crediting_period_end": rec.get("creditingPeriodEndDate", ""),
                    "registration_date": reg_date,
                    "detail_url": (
                        f"https://registry.verra.org/app/projectDetail/VCS/{project_id}"
                    ),
                },
            })

        logger.info("Verra Registry returned %d blue carbon projects", len(observations))
        return observations
