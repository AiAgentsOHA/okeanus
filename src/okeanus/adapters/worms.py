"""WoRMS (World Register of Marine Species) REST API adapter.

Provides taxonomic lookups via AphiaID -- the canonical linking key used
across OBIS, GBIF, and Okeanus biological observations.

API docs: https://www.marinespecies.org/rest/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.marinespecies.org/rest/"


class WormsAdapter(BaseAdapter):
    """Connector for the WoRMS taxonomic REST API."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "worms"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "weekly"

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_by_aphia_id(self, aphia_id: int) -> dict[str, Any] | None:
        """Retrieve a single AphiaRecord by its AphiaID.

        Returns *None* when the ID does not exist.
        """
        url = f"{BASE_URL}AphiaRecordByAphiaID/{aphia_id}"
        try:
            resp = await self._request("GET", url)
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (204, 404):
                return None
            raise

    async def search_by_name(
        self, name: str, *, marine_only: bool = True
    ) -> list[dict[str, Any]]:
        """Search AphiaRecords by scientific name.

        Parameters
        ----------
        name:
            Scientific name (exact or partial match handled by the API).
        marine_only:
            Restrict to marine taxa (default *True*).
        """
        url = f"{BASE_URL}AphiaRecordsByName/{name}"
        params: dict[str, Any] = {}
        if marine_only:
            params["marine_only"] = "true"
        try:
            resp = await self._request("GET", url, params=params)
            data = resp.json()
            return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 204:
                return []
            raise

    async def get_classification(self, aphia_id: int) -> dict[str, Any] | None:
        """Retrieve the full taxonomic classification tree for an AphiaID."""
        url = f"{BASE_URL}AphiaClassificationByAphiaID/{aphia_id}"
        try:
            resp = await self._request("GET", url)
            return resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (204, 404):
                return None
            raise

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
        """Fetch marine species records from WoRMS.

        Pass ``names`` list for specific lookups, or defaults to common
        marine vernacular searches.
        """
        names: list[str] = params.get("names", [])
        limit = params.get("limit", 20)

        if not names:
            names = ["dolphin", "whale", "coral", "shark", "tuna"]

        observations: list[dict[str, Any]] = []
        for name in names:
            if len(observations) >= limit:
                break
            url = f"{BASE_URL}AphiaRecordsByVernacular/{name}"
            try:
                resp = await self._request("GET", url, params={"like": "true", "offset": 1})
                records = resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 204:
                    continue
                raise
            except Exception:
                continue

            if not isinstance(records, list):
                continue

            for rec in records:
                if not isinstance(rec, dict):
                    continue
                observations.append({
                    "obs_type": "biological",
                    "timestamp": time_start,
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"worms-{rec.get('AphiaID', '')}",
                    "source_name": "WoRMS",
                    "quality_score": 0.95,
                    "payload": {
                        "aphia_id": rec.get("AphiaID"),
                        "scientific_name": rec.get("scientificname", ""),
                        "authority": rec.get("authority", ""),
                        "status": rec.get("status", ""),
                        "rank": rec.get("rank", ""),
                        "valid_name": rec.get("valid_name", ""),
                        "kingdom": rec.get("kingdom", ""),
                        "phylum": rec.get("phylum", ""),
                        "class": rec.get("class", ""),
                        "order": rec.get("order", ""),
                        "family": rec.get("family", ""),
                        "genus": rec.get("genus", ""),
                        "is_marine": rec.get("isMarine"),
                    },
                })
                if len(observations) >= limit:
                    break

        logger.info("WoRMS returned %d species records", len(observations))
        return observations
