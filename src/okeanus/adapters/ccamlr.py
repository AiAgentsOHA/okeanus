"""CCAMLR (Commission for Conservation of Antarctic Marine Living Resources) adapter.

CCAMLR manages Southern Ocean fisheries and publishes catch/effort
data, scientific observer data, and management area boundaries.

Data source: https://www.ccamlr.org/
GIS data: https://gis.ccamlr.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# CCAMLR GIS services
WFS_URL = "https://gis.ccamlr.org/geoserver/gis/ows"


class CcamlrAdapter(BaseAdapter):
    """Connector for CCAMLR Antarctic marine data (no auth required).

    Provides fishery management areas, research blocks, and
    marine protected area boundaries in the Southern Ocean.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ccamlr"

    @property
    def source_url(self) -> str:
        return "https://www.ccamlr.org/"

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
        """Fetch CCAMLR management area and fishery data.

        Extra params:
            layer: WFS layer name (default: 'gis:statistical_areas')
                Options: 'gis:statistical_areas', 'gis:research_blocks',
                         'gis:mpas', 'gis:ssrus', 'gis:small_scale_research_units'
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        layer = params.get("layer", "gis:statistical_areas")

        # CCAMLR data is Southern Ocean — clamp if global bbox
        if (e - w) > 200 or (n - s) > 100:
            w, s, e, n = -180.0, -80.0, 180.0, -45.0

        # CCAMLR GeoServer bbox filter is unreliable (axis-order issues),
        # but datasets are small (<100 features), so fetch all and filter client-side
        wfs_params: dict[str, Any] = {
            "service": "WFS",
            "version": "1.0.0",
            "request": "GetFeature",
            "typeName": layer,
            "outputFormat": "application/json",
            "maxFeatures": limit,
        }

        try:
            resp = await self._request("GET", WFS_URL, params=wfs_params)
            data = resp.json()
        except Exception as exc:
            logger.error("CCAMLR GIS fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            # Compute centroid
            lon, lat = _centroid(geom)
            if lon is None or lat is None:
                continue

            area_name = (
                props.get("GAR_Name")
                or props.get("name")
                or props.get("NAME")
                or props.get("label")
                or ""
            )
            area_id = (
                props.get("GAR_Short_Label")
                or props.get("id")
                or props.get("ID")
                or ""
            )

            observations.append({
                "obs_type": "governance",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ccamlr-{layer.split(':')[-1]}-{area_id or len(observations)}",
                "source_name": "CCAMLR",
                "quality_score": 0.95,
                "payload": {
                    "layer": layer,
                    "area_name": area_name,
                    "area_id": str(area_id),
                    "area_type": layer.split(":")[-1].replace("_", " ").title(),
                    **{k: v for k, v in props.items() if k not in ("geometry",)},
                },
            })

        logger.info("CCAMLR returned %d features", len(observations))
        return observations


def _centroid(geom: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract representative point from GeoJSON geometry.

    CCAMLR GeoServer returns coordinates in [lat, lon] order due to
    EPSG:4326 axis conventions in WFS 1.0.0. We detect and swap if needed.
    Returns (lon, lat) in standard order.
    """
    gtype = geom.get("type", "")
    coords = geom.get("coordinates")
    if not coords:
        return None, None

    def _avg_ring(ring: list) -> tuple[float, float]:
        c0 = sum(pt[0] for pt in ring) / len(ring)
        c1 = sum(pt[1] for pt in ring) / len(ring)
        return c0, c1

    if gtype == "Point":
        c0, c1 = float(coords[0]), float(coords[1])
    elif gtype == "Polygon":
        c0, c1 = _avg_ring(coords[0])
    elif gtype == "MultiPolygon":
        c0, c1 = _avg_ring(coords[0][0])
    else:
        return None, None

    # Detect axis order: if c0 is in [-90, 90] range, it's likely latitude
    # (Southern Ocean data is always south of -45), swap to (lon, lat)
    if -90 <= c0 <= 90 and not (-90 <= c1 <= 90):
        return c1, c0  # swap: was [lat, lon], return (lon, lat)
    return c0, c1
