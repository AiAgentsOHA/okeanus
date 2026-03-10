"""IMB Piracy Reporting Centre adapter — global piracy incidents.

International Maritime Bureau (ICC-IMB) piracy and armed robbery incidents.
Uses the IMB Live Piracy Map data feed. No auth required.

Data source: https://www.icc-ccs.org/piracy-reporting-centre
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.icc-ccs.org/piracy-reporting-centre/live-piracy-map"


class ImbPiracyAdapter(BaseAdapter):
    """Connector for IMB piracy incident data (no auth required).

    Fetches recent piracy/armed robbery incidents from the IMB live map
    data feed.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, **kwargs)

    @property
    def source_name(self) -> str:
        return "imb_piracy"

    @property
    def source_url(self) -> str:
        return "https://www.icc-ccs.org/piracy-reporting-centre"

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
        """Fetch piracy incidents within bbox and time range.

        Fetches the IMB incident feed and filters by bbox/time client-side.

        Extra params:
            incident_type: 'actual', 'attempted', or 'all' (default)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 200)

        # IMB provides a KML/JSON feed of recent incidents
        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/json",
                params={"year": time_end.year},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("IMB Piracy fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("incidents", data.get("features", []))
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

            lon, lat = float(lon), float(lat)

            # Filter by bbox
            if not (w <= lon <= e and s <= lat <= n):
                continue

            date_str = props.get("date") or props.get("incidentDate", "")
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                elif len(str(date_str)) >= 10:
                    ts = datetime.fromisoformat(str(date_str)[:10] + "T00:00:00+00:00")
                else:
                    continue
            except (ValueError, AttributeError):
                continue

            # Filter by time
            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"imb-{props.get('id', props.get('incidentId', ''))}",
                "source_name": "IMB Piracy",
                "quality_score": 0.9,
                "payload": {
                    "incident_type": props.get("type", props.get("incidentType", "")),
                    "narration": str(props.get("narration", props.get("description", "")))[:500],
                    "vessel_name": props.get("vesselName", ""),
                    "vessel_type": props.get("vesselType", ""),
                    "flag": props.get("flag", ""),
                    "status": props.get("status", ""),
                    "area": props.get("area", props.get("region", "")),
                    "country_nearest": props.get("countryNearest", ""),
                },
            })

            if len(observations) >= limit:
                break

        logger.info("IMB Piracy returned %d incidents", len(observations))
        return observations
