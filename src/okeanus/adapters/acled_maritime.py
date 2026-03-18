"""ACLED Maritime adapter — maritime conflict and security events.

The Armed Conflict Location & Event Data Project (ACLED) tracks political
violence, protests, and strategic events globally. This adapter filters
for maritime-related events using keyword and location filters.
Requires a free API key (register at acleddata.com).

Source: https://acleddata.com/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ACLED_API = "https://api.acleddata.com/acled/read"

# Maritime-related event subtypes and keywords
MARITIME_TERMS = [
    "naval", "maritime", "port", "ship", "vessel", "piracy", "pirate",
    "coast guard", "coastguard", "fishing", "sea", "ocean", "offshore",
    "strait", "channel", "gulf", "harbor", "harbour",
]


class AcledMaritimeAdapter(BaseAdapter):
    """Connector for ACLED maritime conflict events (free API key required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)
        self._api_key = os.environ.get("ACLED_API_KEY", "")
        self._email = os.environ.get("ACLED_EMAIL", "")

    @property
    def source_name(self) -> str:
        return "acled_maritime"

    @property
    def source_url(self) -> str:
        return "https://acleddata.com/"

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch maritime conflict events from ACLED.

        Extra params:
            event_type: Filter by event type (e.g. 'Battles', 'Violence against civilians')
            limit: Max records (default 200)
        """
        if not self._api_key or not self._email:
            logger.error("ACLED requires ACLED_API_KEY and ACLED_EMAIL env vars")
            return []

        w, s, e, n = bbox
        limit = params.get("limit", 200)
        event_type = params.get("event_type", "")

        api_params: dict[str, Any] = {
            "key": self._api_key,
            "email": self._email,
            "event_date": f"{time_start.strftime('%Y-%m-%d')}|{time_end.strftime('%Y-%m-%d')}",
            "event_date_where": "BETWEEN",
            "latitude": f"{s}|{n}",
            "latitude_where": "BETWEEN",
            "longitude": f"{w}|{e}",
            "longitude_where": "BETWEEN",
            "limit": limit,
        }
        if event_type:
            api_params["event_type"] = event_type

        try:
            resp = await self._request("GET", ACLED_API, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("ACLED fetch failed: %s", exc)
            return []

        records = data.get("data", [])
        observations: list[dict[str, Any]] = []

        for rec in records:
            lat = rec.get("latitude")
            lon = rec.get("longitude")
            if lat is None or lon is None:
                continue

            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue

            # Filter for maritime relevance via notes/location keywords
            notes = str(rec.get("notes", "")).lower()
            location = str(rec.get("location", "")).lower()
            combined = notes + " " + location
            is_maritime = any(term in combined for term in MARITIME_TERMS)
            if not is_maritime:
                continue

            date_str = rec.get("event_date", "")
            try:
                ts = datetime.fromisoformat(date_str + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "security_event",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"acled-{rec.get('data_id', '')}",
                "source_name": "ACLED",
                "quality_score": 0.9,
                "payload": {
                    "event_type": rec.get("event_type", ""),
                    "sub_event_type": rec.get("sub_event_type", ""),
                    "actor1": rec.get("actor1", ""),
                    "actor2": rec.get("actor2", ""),
                    "country": rec.get("country", ""),
                    "admin1": rec.get("admin1", ""),
                    "location": rec.get("location", ""),
                    "fatalities": rec.get("fatalities"),
                    "notes": rec.get("notes", "")[:500],
                    "source": rec.get("source", ""),
                },
            })

        logger.info("ACLED maritime returned %d events", len(observations))
        return observations
