"""NOAA Storm Events adapter — severe weather events affecting oceans.

Storm events from NOAA's Severe Weather Data Inventory (SWDI) and the
Storm Events Database. Covers marine weather events like tropical
cyclones, waterspouts, and coastal floods. No auth required.

Data source: https://www.ncdc.noaa.gov/stormevents/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ncei.noaa.gov/access/services/search/v1/data"


class NoaaStormEventsAdapter(BaseAdapter):
    """Connector for NOAA Storm Events (no auth required).

    Queries the NCEI search API for severe weather events filtered
    by bounding box and time range.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_storm_events"

    @property
    def source_url(self) -> str:
        return "https://www.ncdc.noaa.gov/stormevents/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch storm events within bbox and time range.

        Extra params:
            event_type: filter by event type (e.g. 'Hurricane', 'Marine Thunderstorm Wind')
            limit: Max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        event_type = params.get("event_type")

        query_params: dict[str, Any] = {
            "dataset": "NCDC-STORM-EVENTS",
            "bbox": f"{w},{s},{e},{n}",
            "startDate": time_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endDate": time_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "limit": limit,
            "format": "json",
        }

        if event_type:
            query_params["eventType"] = event_type

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA Storm Events fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("results", data.get("events", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("longitude", rec.get("BEGIN_LON"))
            lat = rec.get("latitude", rec.get("BEGIN_LAT"))
            if lon is None or lat is None:
                continue

            try:
                lon, lat = float(lon), float(lat)
            except (ValueError, TypeError):
                continue

            date_str = rec.get("beginDate", rec.get("BEGIN_DATE_TIME", ""))
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                elif date_str:
                    ts = datetime.fromisoformat(str(date_str)[:10])
                else:
                    ts = time_start
            except (ValueError, AttributeError):
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"noaa-storm-{rec.get('id', rec.get('EVENT_ID', ''))}",
                "source_name": "NOAA Storm Events",
                "quality_score": 0.85,
                "payload": {
                    "event_type": rec.get("eventType", rec.get("EVENT_TYPE", "")),
                    "state": rec.get("state", rec.get("STATE", "")),
                    "begin_date": rec.get("beginDate", rec.get("BEGIN_DATE_TIME", "")),
                    "end_date": rec.get("endDate", rec.get("END_DATE_TIME", "")),
                    "magnitude": rec.get("magnitude", rec.get("MAGNITUDE")),
                    "injuries": rec.get("injuries", rec.get("INJURIES_DIRECT")),
                    "deaths": rec.get("deaths", rec.get("DEATHS_DIRECT")),
                    "damage_property": rec.get("damageProperty", rec.get("DAMAGE_PROPERTY", "")),
                    "source": rec.get("source", rec.get("SOURCE", "")),
                },
            })

        logger.info("NOAA Storm Events returned %d events", len(observations))
        return observations
