"""Marine Debris Tracker adapter — citizen science ocean debris data.

Global marine debris observations collected via the Marine Debris Tracker
mobile app (partnership between NOAA and UGA). No auth required.

Data portal: https://marinedebris.noaa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://marinedebris.noaa.gov/mdmap/api"


class MarineDebrisAdapter(BaseAdapter):
    """Connector for NOAA Marine Debris monitoring data (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "marine_debris"

    @property
    def source_url(self) -> str:
        return "https://marinedebris.noaa.gov/"

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
        """Fetch marine debris observations within bbox and time range.

        Extra params:
            material: Material type filter (e.g. 'Plastic', 'Metal')
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "minLon": w,
            "minLat": s,
            "maxLon": e,
            "maxLat": n,
            "startDate": time_start.strftime("%Y-%m-%d"),
            "endDate": time_end.strftime("%Y-%m-%d"),
            "limit": limit,
            "format": "json",
        }
        if material := params.get("material"):
            api_params["material"] = material

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/observations", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("Marine Debris fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("features", data.get("results", []))
        observations: list[dict[str, Any]] = []

        for rec in results:
            if not isinstance(rec, dict):
                continue

            # Handle GeoJSON-style or flat
            if "geometry" in rec and "properties" in rec:
                coords = rec["geometry"].get("coordinates", [])
                props = rec["properties"]
                lon, lat = (coords[0], coords[1]) if len(coords) >= 2 else (None, None)
            else:
                lon = rec.get("longitude", rec.get("lon"))
                lat = rec.get("latitude", rec.get("lat"))
                props = rec

            if lon is None or lat is None:
                continue

            date_str = props.get("date") or props.get("collectionDate", "")
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                else:
                    ts = datetime.fromisoformat(str(date_str) + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"debris-{props.get('id', props.get('eventId', ''))}",
                "source_name": "Marine Debris Tracker",
                "quality_score": 0.7,
                "payload": {
                    "item_type": props.get("itemType", props.get("material", "")),
                    "material": props.get("material", ""),
                    "count": props.get("count", props.get("quantity")),
                    "weight_kg": props.get("weight"),
                    "location_type": props.get("locationType", ""),
                    "organization": props.get("organization", ""),
                    "event_type": props.get("eventType", ""),
                    "notes": str(props.get("notes", ""))[:300],
                },
            })

        logger.info("Marine Debris returned %d observations", len(observations))
        return observations
