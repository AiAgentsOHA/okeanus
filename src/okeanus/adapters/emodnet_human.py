"""EMODnet Human Activities adapter — offshore infrastructure and activities.

European Marine Observation and Data Network Human Activities provides
data on offshore installations, submarine cables, pipelines, dredging,
wind farms, and other human uses of the sea via WFS. No auth required.

Data portal: https://www.emodnet-humanactivities.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://ows.emodnet-humanactivities.eu/wfs"

# Available layers (typeNames)
LAYERS = {
    "wind_farms": "emodnet:activelicences",
    "cables": "emodnet:submarinecables",
    "pipelines": "emodnet:pipelines",
    "platforms": "emodnet:platforms",
    "dredging": "emodnet:dredging",
    "aquaculture": "emodnet:aquaculture",
}


class EmodnetHumanAdapter(BaseAdapter):
    """Connector for EMODnet Human Activities WFS endpoint (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "emodnet_human"

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
        """Fetch human activity features within bbox.

        Extra params:
            layer: one of 'wind_farms', 'cables', 'pipelines', 'platforms',
                   'dredging', 'aquaculture' (default 'platforms')
            limit: Max features to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        layer = params.get("layer", "platforms")
        type_name = LAYERS.get(layer, LAYERS["platforms"])

        api_params: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": type_name,
            "outputFormat": "application/json",
            "count": limit,
            "bbox": f"{s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326",
        }

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("EMODnet Human Activities fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry")

            if not geom:
                continue

            if geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                else:
                    continue
            elif geom.get("type") in ("LineString", "MultiLineString"):
                # Use midpoint of line
                coords = geom.get("coordinates", [])
                if geom["type"] == "MultiLineString" and coords:
                    line = coords[0]
                else:
                    line = coords
                if line:
                    mid = line[len(line) // 2]
                    lon, lat = mid[0], mid[1]
                else:
                    continue
            elif geom.get("type") in ("Polygon", "MultiPolygon"):
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
                "source_id": f"emodnet-human-{layer}-{props.get('gml_id', props.get('id', ''))}",
                "source_name": "EMODnet Human Activities",
                "quality_score": 0.8,
                "payload": {
                    "layer": layer,
                    "name": props.get("name", props.get("NAME", "")),
                    "country": props.get("country", props.get("COUNTRY", "")),
                    "status": props.get("status", props.get("STATUS", "")),
                    "operator": props.get("operator", props.get("OPERATOR", "")),
                    "type": props.get("type", props.get("TYPE", "")),
                    "year": props.get("year", props.get("YEAR", "")),
                },
            })

        logger.info("EMODnet Human Activities returned %d features (%s)", len(observations), layer)
        return observations
