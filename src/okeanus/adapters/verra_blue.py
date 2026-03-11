"""Verra VCS blue carbon credits adapter via Climate Action Data Trust.

Blue carbon project registrations, credits issued, and retirements
from Verra's Verified Carbon Standard, accessed through the open
CAD Trust API that aggregates all major registries.

API: REST at climateactiondata.org.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.climateactiondata.org/v1"

# Blue carbon methodology codes
BLUE_CARBON_METHODOLOGIES = [
    "VM0007",  # REDD+ Methodology Framework (mangroves)
    "VM0024",  # Methodology for Coastal Wetland Creation
    "VM0033",  # Methodology for Tidal Wetland Restoration
    "VM0036",  # Methodology for Rewetting Drained Temperate Peatlands (coastal)
    "VCS",     # General VCS (filter by project type)
]

BLUE_PROJECT_TYPES = [
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
    """Connector for Verra VCS via CAD Trust — blue carbon credits (no auth).

    Returns blue carbon project data including credits issued,
    retired, and available, with project locations and methodologies.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "verra_blue"

    @property
    def source_url(self) -> str:
        return "https://climateactiondata.org/"

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
        """Fetch blue carbon credit data from CAD Trust / Verra.

        Extra params:
            registry: 'verra' (default), 'gold_standard', or 'all'
            query: search term (default: 'blue carbon OR mangrove OR seagrass')
            country: ISO2 country code
            limit: max records (default: 200)
        """
        registry = params.get("registry", "verra")
        query = params.get("query", "blue carbon OR mangrove OR seagrass OR tidal wetland")
        country = params.get("country")
        limit = params.get("limit", 200)

        url = f"{BASE_URL}/projects"
        query_params: dict[str, Any] = {
            "q": query,
            "limit": limit,
        }
        if registry != "all":
            query_params["registry"] = registry
        if country:
            query_params["country"] = country

        try:
            resp = await self._request("GET", url, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("CAD Trust fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("projects", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            project_id = rec.get("id") or rec.get("projectId") or rec.get("vcsId", "")
            name = rec.get("name") or rec.get("title") or ""

            # Check if it's actually a blue carbon project
            name_lower = name.lower()
            desc_lower = (rec.get("description") or "").lower()
            is_blue = any(
                kw in name_lower or kw in desc_lower
                for kw in BLUE_PROJECT_TYPES
            )
            methodology = rec.get("methodology") or rec.get("methodologyCode") or ""
            if methodology in BLUE_CARBON_METHODOLOGIES:
                is_blue = True

            if not is_blue and query == "blue carbon OR mangrove OR seagrass OR tidal wetland":
                continue

            # Parse dates
            start_date = rec.get("startDate") or rec.get("creditingPeriodStart") or ""
            try:
                ts = datetime.strptime(start_date[:10], "%Y-%m-%d") if start_date else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            # Location
            lat = rec.get("latitude") or rec.get("lat") or 0.0
            lon = rec.get("longitude") or rec.get("lng") or rec.get("lon") or 0.0

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)],
                },
                "source_id": f"verra-{project_id}",
                "source_name": "Verra VCS / CAD Trust",
                "quality_score": 0.93,
                "payload": {
                    "project_id": str(project_id),
                    "name": name,
                    "registry": rec.get("registry", registry),
                    "country": rec.get("country") or rec.get("countryCode", ""),
                    "methodology": methodology,
                    "project_type": rec.get("projectType") or rec.get("type", ""),
                    "status": rec.get("status", ""),
                    "credits_issued": rec.get("creditsIssued") or rec.get("totalCreditsIssued"),
                    "credits_retired": rec.get("creditsRetired") or rec.get("totalCreditsRetired"),
                    "credits_available": rec.get("creditsAvailable"),
                    "vintage_start": rec.get("vintageStart"),
                    "vintage_end": rec.get("vintageEnd"),
                    "developer": rec.get("developer") or rec.get("proponent", ""),
                },
            })

        logger.info("Verra/CAD Trust returned %d blue carbon projects", len(observations))
        return observations
