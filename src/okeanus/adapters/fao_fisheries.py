"""FAO Global Fisheries Statistics adapter — capture and aquaculture data.

FAO provides global fisheries and aquaculture production statistics
via the FishStatJ platform and WFS GeoServer.

The FAO GeoServer provides fishery statistical areas (FAO major
fishing areas 18/27/34/etc) and associated catch data.

Data source: https://www.fao.org/fishery/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# FAO GeoServer for fishery areas
WFS_URL = "https://www.fao.org/fishery/geoserver/fifao/ows"

# FAO SDG indicator API (fisheries sustainability)
SDG_URL = "https://unstats.un.org/sdgapi/v1/sdg/Indicator/Data"


class FaoFisheriesAdapter(BaseAdapter):
    """Connector for FAO fishery area data via WFS (no auth required).

    Returns FAO major fishing area boundaries and metadata via
    the FAO Fisheries GeoServer WFS endpoint.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fao_fisheries"

    @property
    def source_url(self) -> str:
        return "https://www.fao.org/fishery/"

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
        """Fetch FAO fishery area data via WFS.

        Extra params:
            layer: WFS layer (default 'fifao:FAO_MAJOR')
                Options: 'fifao:FAO_MAJOR' (major fishing areas),
                         'fifao:FAO_SUB_AREA', 'fifao:FAO_DIV'
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        layer = params.get("layer", "fifao:FAO_MAJOR")

        wfs_params: dict[str, Any] = {
            "service": "WFS",
            "version": "1.0.0",
            "request": "GetFeature",
            "typeName": layer,
            "outputFormat": "application/json",
            "maxFeatures": limit,
            "bbox": f"{s},{w},{n},{e}",
        }

        try:
            resp = await self._request("GET", WFS_URL, params=wfs_params)
            data = resp.json()
        except Exception as exc:
            logger.error("FAO Fisheries WFS fetch failed: %s", exc)
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

            area_name = props.get("NAME_EN") or props.get("LABEL") or ""
            area_code = props.get("F_CODE") or props.get("F_AREA") or ""
            ocean = props.get("OCEAN") or props.get("ocean", "")

            observations.append({
                "obs_type": "governance",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"fao-area-{area_code}",
                "source_name": "FAO Fisheries",
                "quality_score": 0.95,
                "payload": {
                    "area_name": area_name,
                    "area_code": str(area_code),
                    "ocean": ocean,
                    "area_type": props.get("F_LEVEL", ""),
                    "status": props.get("F_STATUS", ""),
                },
            })

        logger.info("FAO Fisheries returned %d areas", len(observations))
        return observations


def _centroid(geom: dict[str, Any]) -> tuple[float | None, float | None]:
    """Extract representative point from GeoJSON geometry."""
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
        ring = coords[0][0]
        lon = sum(pt[0] for pt in ring) / len(ring)
        lat = sum(pt[1] for pt in ring) / len(ring)
        return lon, lat
    return None, None
