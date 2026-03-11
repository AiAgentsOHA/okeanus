"""EMODnet Seabed Habitats adapter — EU seabed habitat classifications.

European Marine Observation and Data Network Seabed Habitats provides
classified seabed habitat maps across European seas via WFS.
No auth required.

Data portal: https://www.emodnet-seabedhabitats.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://ows.emodnet-seabedhabitats.eu/geoserver/emodnet_open/wfs"


class EmodnetSeabedAdapter(BaseAdapter):
    """Connector for EMODnet Seabed Habitats WFS endpoint (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "emodnet_seabed"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch seabed habitat classifications within bbox.

        Extra params:
            habitat_type: EUNIS habitat code filter (e.g. 'A5.13')
            limit: Max features to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": "emodnet_open:euseamap_2023",
            "outputFormat": "application/json",
            "count": limit,
            "bbox": f"{s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326",
        }

        habitat_type = params.get("habitat_type")
        if habitat_type:
            api_params["cql_filter"] = f"eunis_code LIKE '{habitat_type}%'"

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("EMODnet Seabed Habitats fetch failed: %s", exc)
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
            elif geom and geom.get("type") in ("Polygon", "MultiPolygon"):
                # Use centroid of first polygon ring
                coords = geom.get("coordinates", [])
                if geom["type"] == "MultiPolygon" and coords:
                    ring = coords[0][0] if coords[0] else []
                elif coords:
                    ring = coords[0]
                else:
                    continue
                if ring:
                    lon = sum(pt[0] for pt in ring) / len(ring)
                    lat = sum(pt[1] for pt in ring) / len(ring)
                else:
                    continue
            else:
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"emodnet-seabed-{props.get('gml_id', props.get('id', ''))}",
                "source_name": "EMODnet Seabed Habitats",
                "quality_score": 0.85,
                "payload": {
                    "eunis_code": props.get("eunis_code", ""),
                    "eunis_name": props.get("eunis_name", props.get("habitat", "")),
                    "substrate": props.get("substrate", ""),
                    "biological_zone": props.get("bioz", props.get("biological_zone", "")),
                    "energy_level": props.get("energy", ""),
                    "confidence": props.get("confidence", ""),
                    "survey_year": props.get("survey_year", ""),
                },
            })

        logger.info("EMODnet Seabed Habitats returned %d features", len(observations))
        return observations
