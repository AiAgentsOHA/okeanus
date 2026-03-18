"""Global Fishing Watch adapter.

Fishing effort, vessel identity, fishing events, encounters,
transshipment, loitering, port visits, IUU risk scoring.

API docs: https://globalfishingwatch.org/our-apis/documentation
Note: Requires a free API key from https://globalfishingwatch.org/our-apis/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://gateway.api.globalfishingwatch.org/v3"

VESSEL_DATASET = "public-global-vessel-identity:latest"


class GlobalFishingWatchAdapter(BaseAdapter):
    """Connector for Global Fishing Watch API (free API key required)."""

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._api_key = api_key or os.environ.get("GFW_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "gfw"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "daily"

    def _auth_headers(self) -> dict[str, str]:
        if self._api_key:
            return {"Authorization": f"Bearer {self._api_key}"}
        return {}

    async def search_vessels(self, query: str) -> list[dict[str, Any]]:
        """Search for vessels by name, MMSI, IMO, or callsign."""
        if not self._api_key:
            logger.warning("GFW adapter requires api_key")
            return []
        params = {
            "query": query,
            "limit": 20,
            "datasets[]": VESSEL_DATASET,
        }
        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/vessels/search",
                params=params, headers=self._auth_headers(),
            )
            data = resp.json()
            return data.get("entries", [])
        except Exception as exc:
            logger.error("GFW vessel search failed: %s", exc)
            return []

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch fishing events or vessel tracks within bbox/time.

        Pass ``endpoint`` in params: 'events' (default), 'vessels'.
        """
        if not self._api_key:
            logger.warning(
                "GFW adapter requires api_key"
                " (free at globalfishingwatch.org)",
            )
            return []

        endpoint = params.get("endpoint", "events")
        event_type = params.get("event_type", "fishing")
        limit = params.get("limit", 100)

        if endpoint == "vessels":
            query = params.get("query", "")
            if not query:
                return []
            return await self._fetch_vessel_search(query)

        return await self._fetch_events(
            bbox, time_start, time_end, event_type, limit,
        )

    async def _fetch_events(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        event_type: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch fishing/encounter/loitering events."""
        w, s, e, n = bbox
        dataset = f"public-global-{event_type}-events:latest"
        body: dict[str, Any] = {
            "datasets": [dataset],
            "startDate": time_start.strftime("%Y-%m-%d"),
            "endDate": time_end.strftime("%Y-%m-%d"),
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[w, s], [e, s], [e, n], [w, n], [w, s]],
                ],
            },
        }

        try:
            resp = await self._request(
                "POST",
                f"{BASE_URL}/events?limit={limit}&offset=0",
                json=body,
                headers=self._auth_headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("GFW events fetch failed: %s", exc)
            return []

        entries = data.get("entries", [])

        observations: list[dict[str, Any]] = []
        for event in entries:
            pos = event.get("position", {})
            lon = pos.get("lon", 0.0)
            lat = pos.get("lat", 0.0)

            ts_str = event.get("start", "")
            try:
                ts = datetime.fromisoformat(
                    ts_str.replace("Z", "+00:00"),
                )
            except (ValueError, AttributeError):
                continue

            vessel = event.get("vessel", {})

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat],
                },
                "source_id": f"gfw-{event.get('id', '')}",
                "source_name": "Global Fishing Watch",
                "mmsi": vessel.get("ssvid"),
                "quality_score": None,
                "payload": {
                    "event_type": event_type,
                    "vessel_name": vessel.get("name", ""),
                    "vessel_flag": vessel.get("flag", ""),
                    "vessel_type": vessel.get("type", ""),
                    "duration_hours": event.get(
                        "durationHrs",
                    ),
                    "event_end": event.get("end"),
                    "distance_from_shore_km": (
                        event.get("distances", {}).get(
                            "startDistanceFromShoreKm",
                        )
                    ),
                },
            })

        logger.info(
            "GFW returned %d %s events",
            len(observations), event_type,
        )
        return observations

    async def _fetch_vessel_search(
        self, query: str,
    ) -> list[dict[str, Any]]:
        """Search vessels and return as observation dicts."""
        vessels = await self.search_vessels(query)
        observations: list[dict[str, Any]] = []
        for v in vessels:
            # Extract best name from selfReportedInfo
            info = v.get("selfReportedInfo", [{}])
            best = info[0] if info else {}

            observations.append({
                "obs_type": "vessel",
                "timestamp": datetime.now(),
                "geometry": {
                    "type": "Point",
                    "coordinates": [0, 0],
                },
                "source_id": f"gfw-vessel-{v.get('id', best.get('id',''))}",
                "source_name": "Global Fishing Watch",
                "mmsi": best.get("ssvid"),
                "quality_score": None,
                "payload": {
                    "vessel_name": best.get("shipname", ""),
                    "flag": best.get("flag", ""),
                    "vessel_type": best.get("shiptype", ""),
                    "imo": best.get("imo"),
                    "callsign": best.get("callsign"),
                    "gear_type": best.get("geartype", ""),
                },
            })
        return observations
