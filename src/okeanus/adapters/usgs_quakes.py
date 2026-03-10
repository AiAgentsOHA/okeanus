"""USGS Earthquake Hazards Program adapter — undersea earthquakes and tsunamis.

Real-time earthquake data from the USGS FDSNWS Event service. Returns
seismic events as GeoJSON features with magnitude, depth, tsunami flags.

API docs: https://earthquake.usgs.gov/fdsnws/event/1/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


class UsgsQuakesAdapter(BaseAdapter):
    """Connector for USGS Earthquake Hazards Program (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "usgs_quakes"

    @property
    def source_url(self) -> str:
        return "https://earthquake.usgs.gov/"

    @property
    def update_frequency(self) -> str:
        return "real-time"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch earthquake events within bbox and time range.

        Extra params:
            limit: Maximum number of results (default 500)
            min_magnitude: Minimum magnitude filter
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        min_magnitude = params.get("min_magnitude")

        query_params: dict[str, Any] = {
            "format": "geojson",
            "starttime": time_start.isoformat(),
            "endtime": time_end.isoformat(),
            "minlatitude": s,
            "maxlatitude": n,
            "minlongitude": w,
            "maxlongitude": e,
            "limit": limit,
            "orderby": "time",
        }

        if min_magnitude is not None:
            query_params["minmagnitude"] = min_magnitude

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("USGS Earthquake fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            geometry = feat.get("geometry")
            props = feat.get("properties", {})

            if geometry is None:
                continue

            coords = geometry.get("coordinates", [])
            if len(coords) < 3:
                continue

            lon, lat, depth_km = coords[0], coords[1], coords[2]

            time_ms = props.get("time")
            if time_ms is None:
                continue
            try:
                ts = datetime.utcfromtimestamp(time_ms / 1000.0)
            except (ValueError, TypeError, OSError):
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"usgs-quake-{feat.get('id', '')}",
                "source_name": "USGS Earthquakes",
                "quality_score": 0.95,
                "payload": {
                    "magnitude": props.get("mag"),
                    "magnitude_type": props.get("magType", ""),
                    "place": props.get("place", ""),
                    "tsunami": bool(props.get("tsunami", 0)),
                    "depth_km": depth_km,
                    "felt": props.get("felt"),
                    "alert": props.get("alert"),
                    "significance": props.get("sig"),
                    "event_type": props.get("type", ""),
                    "title": props.get("title", ""),
                    "url": props.get("url", ""),
                },
            })

        logger.info("USGS Earthquakes returned %d events", len(observations))
        return observations
