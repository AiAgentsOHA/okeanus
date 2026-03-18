"""NOAA Marine Cadastre adapter — ocean planning and boundary data.

Marine Cadastre provides authoritative ocean boundary data including
OCS lease blocks, wind energy areas, marine protected areas,
shipping lanes, and jurisdictional boundaries.

Data served via ArcGIS REST services. No auth required.

Data source: https://marinecadastre.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Marine Cadastre ArcGIS REST services
ARCGIS_BASE = "https://services7.arcgis.com/G5Ma95RzqJRPKsWL/arcgis/rest/services"

# Key datasets (BOEM migrated to services7.arcgis.com)
LAYERS = {
    "wind_planning_areas": f"{ARCGIS_BASE}/Wind_Planning_Areas__BOEM_/FeatureServer/7/query",
    "wind_leases": f"{ARCGIS_BASE}/Wind_Lease_Boundaries__BOEM_/FeatureServer/8/query",
}


class NoaaMarineCadastreAdapter(BaseAdapter):
    """Connector for Marine Cadastre ocean planning data (no auth required).

    Provides OCS boundaries, wind energy areas, shipping lanes,
    marine protected areas, and other ocean use data.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_marine_cadastre"

    @property
    def source_url(self) -> str:
        return "https://marinecadastre.gov/"

    @property
    def update_frequency(self) -> str:
        return "quarterly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch Marine Cadastre boundary/planning data.

        Extra params:
            layer: 'wind_planning_areas' (default), 'wind_leases',
                   'shipping_fairways', 'marine_protected_areas', 'danger_zones'
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        layer = params.get("layer", "wind_planning_areas")

        url = LAYERS.get(layer, LAYERS["wind_planning_areas"])

        api_params: dict[str, Any] = {
            "where": "1=1",
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": limit,
            "f": "json",
        }

        try:
            resp = await self._request("GET", url, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Marine Cadastre fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            geom = feat.get("geometry", {})
            attrs = feat.get("attributes", {})

            # Get centroid from geometry
            if "x" in geom and "y" in geom:
                lon, lat = float(geom["x"]), float(geom["y"])
            elif "rings" in geom:
                ring = geom["rings"][0]
                lon = sum(pt[0] for pt in ring) / len(ring)
                lat = sum(pt[1] for pt in ring) / len(ring)
            else:
                continue

            name = (
                attrs.get("PROTECTNAME")
                or attrs.get("LEASE_NUMBER")
                or attrs.get("PROT_NAME")
                or attrs.get("objectName")
                or attrs.get("NAME")
                or attrs.get("AREA_NAME")
                or ""
            )

            obj_id = attrs.get("OBJECTID") or attrs.get("FID") or len(observations)

            observations.append({
                "obs_type": "governance",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"mc-{layer}-{obj_id}",
                "source_name": "Marine Cadastre",
                "quality_score": 0.95,
                "payload": {
                    "layer": layer,
                    "name": name,
                    **{k: v for k, v in attrs.items() if k != "Shape"},
                },
            })

        logger.info("Marine Cadastre returned %d features", len(observations))
        return observations
