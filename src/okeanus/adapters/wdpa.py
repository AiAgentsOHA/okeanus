"""WDPA (World Database on Protected Areas) adapter.

Marine protected areas from the Protected Planet API.
Enables "is this vessel inside a protected area?" queries.

API docs: https://api.protectedplanet.net/
Note: Requires a free API token from https://api.protectedplanet.net/request
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.protectedplanet.net/v3"


class WdpaAdapter(BaseAdapter):
    """Connector for the Protected Planet / WDPA API (free token required)."""

    def __init__(self, *, api_token: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_token = api_token

    @property
    def source_name(self) -> str:
        return "wdpa"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def search_by_point(self, lat: float, lon: float) -> list[dict[str, Any]]:
        """Find protected areas containing a given point."""
        if not self._api_token:
            logger.warning("WDPA adapter requires api_token (get free at protectedplanet.net)")
            return []
        params = {
            "token": self._api_token,
            "latitude": lat,
            "longitude": lon,
            "marine": "true",
        }
        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/protected_areas/search", params=params,
            )
            data = resp.json()
            return data.get("protected_areas", [])
        except Exception as exc:
            logger.error("WDPA point search failed: %s", exc)
            return []

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Search for marine protected areas.

        WDPA API supports search by name or country; bbox search is done
        via center-point proximity.
        """
        if not self._api_token:
            logger.warning("WDPA adapter requires api_token")
            return []

        query = params.get("query", "")
        api_params: dict[str, Any] = {
            "token": self._api_token,
            "marine": "true",
            "per_page": params.get("limit", 50),
        }
        if query:
            api_params["q"] = query

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/protected_areas/search", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("WDPA fetch failed: %s", exc)
            return []

        areas = data.get("protected_areas", [])
        observations: list[dict[str, Any]] = []

        for area in areas:
            geo = area.get("geojson", {})
            lon = area.get("longitude", 0.0)
            lat = area.get("latitude", 0.0)
            mrgid = area.get("marine_regions_id")

            observations.append({
                "obs_type": "physical",
                "timestamp": datetime.now(),
                "geometry": geo if geo else {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"wdpa-{area.get('wdpa_id', area.get('id', ''))}",
                "source_name": "WDPA",
                "mrgid": int(mrgid) if mrgid else None,
                "quality_score": None,
                "payload": {
                    "name": area.get("name", ""),
                    "wdpa_id": area.get("wdpa_id"),
                    "iucn_category": area.get("iucn_category", {}).get("name", ""),
                    "designation": area.get("designation", {}).get("name", ""),
                    "country": area.get("countries", [{}])[0].get("name", "")
                    if area.get("countries") else "",
                    "reported_marine_area_km2": area.get("reported_marine_area"),
                    "management_authority": area.get("management_authority", {}).get("name", ""),
                    "is_marine": True,
                },
            })

        logger.info("WDPA returned %d protected areas", len(observations))
        return observations
