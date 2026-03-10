"""EMODnet Biology adapter — EU marine species observations.

European Marine Observation and Data Network (EMODnet) Biology provides
access to marine species occurrence data across European seas via a
WFS (Web Feature Service) endpoint. No auth required.

Data portal: https://www.emodnet-biology.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://geo.vliz.be/geoserver/Dataportal/wfs"


class EmodnetBiologyAdapter(BaseAdapter):
    """Connector for EMODnet Biology WFS endpoint (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "emodnet_biology"

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
        """Fetch marine species observations from EMODnet Biology.

        Extra params:
            limit: Max features to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "Dataportal:eurobis-obisenv",
            "outputFormat": "application/json",
            "count": limit,
            "bbox": f"{s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326",
        }

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("EMODnet Biology fetch failed: %s", exc)
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

            date_str = props.get("eventdate") or props.get("eventDate")
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
                "source_id": f"emodnet-bio-{props.get('id', '')}",
                "source_name": "EMODnet Biology",
                "quality_score": 0.85,
                "payload": {
                    "scientific_name": props.get("scientificname", ""),
                    "aphia_id": props.get("aphiaid") or props.get("aphiaID"),
                    "dataset_name": props.get("datasetname", ""),
                    "event_date": date_str or "",
                    "depth_m": props.get("depth") or props.get("minimumdepthinmeters"),
                    "basis_of_record": props.get("basisofrecord", ""),
                    "institution": props.get("institutioncode", ""),
                },
            })

        logger.info("EMODnet Biology returned %d observations", len(observations))
        return observations
