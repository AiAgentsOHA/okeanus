"""Allen Coral Atlas adapter — global coral reef mapping.

The Allen Coral Atlas provides satellite-derived global coral reef maps
including geomorphic zonation and benthic habitat at 5m resolution.
Data accessible via ArcGIS REST API. No auth required.

Data source: https://allencoralatlas.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://allencoralatlas.org/api/mapping/geomorphic"
)
ARCGIS_URL = (
    "https://tiles.arcgis.com/tiles/rYg6fViuRYaCAXiB/arcgis/rest/services"
    "/ACA_geomorphic/FeatureServer/0/query"
)


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
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        zone_type = params.get("zone_type")

        where = "1=1"
        if zone_type:
            where = f"class_name = '{zone_type}'"

        api_params: dict[str, Any] = {
            "where": where,
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "returnCentroid": "true",
            "resultRecordCount": limit,
            "f": "json",
        }

        try:
            resp = await self._request("GET", ARCGIS_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Allen Coral Atlas fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            geom = feat.get("geometry", {})
            attrs = feat.get("attributes", {})

            centroid = feat.get("centroid")
            if centroid:
                lon = centroid.get("x")
                lat = centroid.get("y")
            elif "rings" in geom and geom["rings"]:
                ring = geom["rings"][0]
                lon = sum(pt[0] for pt in ring) / len(ring) if ring else None
                lat = sum(pt[1] for pt in ring) / len(ring) if ring else None
            else:
                lon = geom.get("x")
                lat = geom.get("y")

            if lon is None or lat is None:
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"aca-{attrs.get('OBJECTID', '')}",
                "source_name": "Allen Coral Atlas",
                "quality_score": 0.9,
                "payload": {
                    "geomorphic_class": attrs.get("class_name", attrs.get("CLASS", "")),
                    "area_sqkm": attrs.get("area_sqkm", attrs.get("Shape_Area")),
                    "reef_system": attrs.get("reef_system", ""),
                    "country": attrs.get("country", ""),
                    "mapping_date": attrs.get("map_date", ""),
                    "confidence": attrs.get("confidence", ""),
                },
            })

        logger.info("Allen Coral Atlas returned %d features", len(observations))
        return observations
