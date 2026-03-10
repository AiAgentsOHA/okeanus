"""OpenSanctions adapter — sanctioned vessels and entities.

Provides lookup of sanctioned vessels by IMO number or name for
compliance screening and IUU vessel flagging.

API docs: https://www.opensanctions.org/docs/api/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.opensanctions.org"


class OpenSanctionsAdapter(BaseAdapter):
    """Connector for OpenSanctions entity search (free for non-commercial)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "opensanctions"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def search_vessel(self, query: str) -> list[dict[str, Any]]:
        """Search for a vessel or entity by name or IMO number."""
        params = {
            "q": query,
            "schema": "Vessel",
            "limit": 20,
        }
        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/search/default", params=params,
            )
            data = resp.json()
            return data.get("results", [])
        except Exception as exc:
            logger.error("OpenSanctions search failed: %s", exc)
            return []

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Search for sanctioned vessels.

        OpenSanctions is not a spatial API — pass ``query`` in params
        to search by vessel name or IMO number.
        """
        query = params.get("query", "")
        if not query:
            logger.info("OpenSanctions requires 'query' param (vessel name or IMO)")
            return []

        results = await self.search_vessel(query)
        observations: list[dict[str, Any]] = []

        for entity in results:
            props = entity.get("properties", {})
            imo_list = props.get("imoNumber", [])
            mmsi_list = props.get("mmsi", [])
            flag_list = props.get("flag", [])
            name_list = props.get("name", [])

            observations.append({
                "obs_type": "vessel",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"sanctions-{entity.get('id', '')}",
                "source_name": "OpenSanctions",
                "mmsi": int(mmsi_list[0]) if mmsi_list else None,
                "quality_score": entity.get("score", 0.0),
                "payload": {
                    "entity_id": entity.get("id", ""),
                    "names": name_list,
                    "imo_numbers": imo_list,
                    "flags": flag_list,
                    "sanctions_datasets": entity.get("datasets", []),
                    "schema": entity.get("schema", ""),
                    "caption": entity.get("caption", ""),
                    "sanctioned": True,
                },
            })

        logger.info("OpenSanctions returned %d entities", len(observations))
        return observations
