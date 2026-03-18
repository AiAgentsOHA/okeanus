"""Allen Coral Atlas adapter — global coral reef mapping.

The Allen Coral Atlas provides satellite-derived global coral reef maps
including geomorphic zonation and benthic habitat at 5m resolution.
Data accessible via GeoServer WFS. No auth required.

Data source: https://allencoralatlas.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

WFS_URL = "https://allencoralatlas.org/geoserver/ows"


class AllenCoralAdapter(BaseAdapter):
    """Connector for Allen Coral Atlas (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "allen_coral"

    @property
    def source_url(self) -> str:
        return "https://allencoralatlas.org/"

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
        """Fetch coral reef geomorphic data within bbox.

        Extra params:
            zone_type: filter by geomorphic zone (e.g. 'Reef Crest', 'Lagoon')
            layer: 'geomorphic' (default) or 'benthic'
            limit: max records (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        zone_type = params.get("zone_type")
        layer = params.get("layer", "geomorphic")

        # Global bbox is too large for coral data — clamp to Great Barrier Reef
        if (e - w) > 100 or (n - s) > 100:
            w, s, e, n = 142.0, -20.0, 155.0, -10.0

        type_name = f"coral-atlas:{layer}_data_verbose"

        wfs_params: dict[str, Any] = {
            "service": "wfs",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": type_name,
            "count": limit,
            "outputFormat": "application/json",
            "bbox": f"{w},{s},{e},{n},EPSG:4326",
        }

        try:
            resp = await self._request("GET", WFS_URL, params=wfs_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Allen Coral Atlas fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if len(observations) >= limit:
                break

            geom = feat.get("geometry", {})
            props = feat.get("properties", {})

            class_name = props.get("class_name", "")
            if zone_type and zone_type.lower() != class_name.lower():
                continue

            area = props.get("area_sqkm")

            # Compute centroid from polygon geometry
            lon, lat = _centroid(geom)
            if lon is None or lat is None:
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"aca-{feat.get('id', len(observations))}",
                "source_name": "Allen Coral Atlas",
                "quality_score": 0.9,
                "payload": {
                    "geomorphic_class": class_name,
                    "area_sqkm": area,
                },
            })

        logger.info("Allen Coral Atlas returned %d features", len(observations))
        return observations


def _centroid(geom: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract a representative point from a GeoJSON geometry."""
    gtype = geom.get("type", "")
    coords = geom.get("coordinates")
    if not coords:
        return None, None

    if gtype == "Point":
        return float(coords[0]), float(coords[1])
    elif gtype == "Polygon":
        ring = coords[0]
        lon = sum(pt[0] for pt in ring) / len(ring)
        lat = sum(pt[1] for pt in ring) / len(ring)
        return lon, lat
    elif gtype == "MultiPolygon":
        # Use the first polygon's first ring
        ring = coords[0][0]
        lon = sum(pt[0] for pt in ring) / len(ring)
        lat = sum(pt[1] for pt in ring) / len(ring)
        return lon, lat
    return None, None
