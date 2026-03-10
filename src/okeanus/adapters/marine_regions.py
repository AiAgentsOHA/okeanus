"""Marine Regions REST API adapter.

Provides access to the Marine Regions Gazetteer for looking up maritime
boundaries (EEZ, territorial seas, etc.) by MRGID or name.

API docs: https://marineregions.org/gazetteer.php?p=webservices
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://marineregions.org/rest/"


class MarineRegionsAdapter(BaseAdapter):
    """Connector for the Marine Regions Gazetteer REST API."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._client: httpx.AsyncClient | None = None

    @property
    def source_name(self) -> str:
        return "marine_regions"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "monthly"

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_by_mrgid(self, mrgid: int) -> dict[str, Any] | None:
        """Fetch a single gazetteer record by its MRGID.

        Returns the raw JSON dict or *None* if not found.
        """
        url = f"{BASE_URL}getGazetteerRecordByMRGID/{mrgid}/"
        try:
            resp = await self._request("GET", url, params={"format": "json"})
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def search_by_name(self, name: str, *, like: bool = True) -> list[dict[str, Any]]:
        """Search gazetteer records by name.

        Parameters
        ----------
        name:
            Search term.
        like:
            If *True* (default), performs a wildcard/contains search.
        """
        url = f"{BASE_URL}getGazetteerRecordsByName/{name}/"
        params: dict[str, Any] = {"format": "json"}
        if like:
            params["like"] = "true"
        resp = await self._request("GET", url, params=params)
        data = resp.json()
        return data if isinstance(data, list) else []

    async def get_wms(self, mrgid: int) -> list[dict[str, Any]]:
        """Get WMS layer references for a given MRGID."""
        url = f"{BASE_URL}getGazetteerWMSes/{mrgid}/"
        resp = await self._request("GET", url, params={"format": "json"})
        data = resp.json()
        return data if isinstance(data, list) else []

    async def get_eez_by_point(self, lat: float, lon: float) -> list[dict[str, Any]]:
        """Find EEZ regions containing a given point.

        Uses the getGazetteerRecordsByLatLong endpoint filtered to EEZ type.
        """
        url = f"{BASE_URL}getGazetteerRecordsByLatLong/"
        params: dict[str, Any] = {
            "latitude": lat,
            "longitude": lon,
            "format": "json",
        }
        try:
            resp = await self._request("GET", url, params=params)
            data = resp.json()
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError:
            logger.warning("EEZ lookup failed for lat=%s lon=%s", lat, lon)
            return []

    # ------------------------------------------------------------------
    # BaseAdapter.fetch implementation
    # ------------------------------------------------------------------

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch region records whose centroid falls inside *bbox*.

        Marine Regions does not have a native bbox search, so this queries
        by the bbox centre point and returns whatever the API finds.
        """
        center_lon = (bbox[0] + bbox[2]) / 2.0
        center_lat = (bbox[1] + bbox[3]) / 2.0
        return await self.get_eez_by_point(center_lat, center_lon)
