"""Ocean Tracking Network (OTN) adapter — animal telemetry data.

Global network for tracking aquatic animals using acoustic, satellite,
and archival tags. Provides movement data for fish, sharks, sea turtles,
and marine mammals. No auth required for public WFS endpoint.

Data portal: https://members.oceantrack.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://members.oceantrack.org/geoserver/otn/wfs"


class OceanTrackingAdapter(BaseAdapter):
    """Connector for Ocean Tracking Network WFS endpoint (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ocean_tracking"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """Fetch animal telemetry records from the Ocean Tracking Network.

        Extra params:
            limit: Max features to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "otn:animals",
            "outputFormat": "application/json",
            "count": limit,
            "bbox": f"{s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326",
        }

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("OTN fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry")

            if geom and geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                else:
                    continue
            else:
                continue

            date_str = (
                props.get("release_date")
                or props.get("date")
                or props.get("eventDate")
            )
            if date_str:
                try:
                    ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    ts = time_start
            else:
                ts = time_start

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"otn-{props.get('id', '')}",
                "source_name": "Ocean Tracking Network",
                "quality_score": 0.9,
                "payload": {
                    "species": props.get("scientificname", ""),
                    "common_name": props.get("commonname", ""),
                    "tag_type": props.get("tag_type", ""),
                    "project": props.get("collectioncode", ""),
                    "release_date": props.get("release_date", ""),
                    "release_location": props.get("release_location", ""),
                    "sex": props.get("sex", ""),
                    "length_cm": props.get("length"),
                },
            })

        logger.info("OTN returned %d animal telemetry records", len(observations))
        return observations
