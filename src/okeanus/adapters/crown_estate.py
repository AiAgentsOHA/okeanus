"""Crown Estate (UK) offshore wind adapter.

All UK offshore wind spatial data including lease areas, cable
routes, and substations for Rounds 1-5 and ScotWind.

API: ArcGIS REST at services.arcgis.com.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://services.arcgis.com"

# Crown Estate / Marine Data Exchange feature services
LAYERS = {
    "offshore_wind_sites": f"{BASE_URL}/JJzESW51TqeY9uat/ArcGIS/rest/services/UK_Offshore_Wind_Farms/FeatureServer/0",
    "cable_routes": f"{BASE_URL}/JJzESW51TqeY9uat/ArcGIS/rest/services/Offshore_Cable_Routes/FeatureServer/0",
    "lease_areas": f"{BASE_URL}/JJzESW51TqeY9uat/ArcGIS/rest/services/Crown_Estate_Lease_Areas/FeatureServer/0",
}


class CrownEstateAdapter(BaseAdapter):
    """Connector for Crown Estate — UK offshore wind (no auth required).

    Returns UK offshore wind farm locations, capacities, operators,
    and cable routes.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "crown_estate"

    @property
    def source_url(self) -> str:
        return "https://www.thecrownestate.co.uk/"

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
        """Fetch UK offshore wind data from Crown Estate.

        Extra params:
            layer: 'offshore_wind_sites' (default), 'cable_routes', 'lease_areas'
            status: filter by project status (e.g. 'Operational', 'Under Construction')
            limit: max features (default: 200)
        """
        layer = params.get("layer", "offshore_wind_sites")
        status = params.get("status")
        limit = params.get("limit", 200)

        url = LAYERS.get(layer, LAYERS["offshore_wind_sites"])
        w, s, e, n = bbox

        where = "1=1"
        if status:
            where = f"Status = '{status}'"

        query: dict[str, Any] = {
            "where": where,
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultRecordCount": limit,
        }

        try:
            resp = await self._request("GET", f"{url}/query", params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("Crown Estate fetch %s failed: %s", layer, exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            coords = geom.get("coordinates", [0, 0])
            if geom.get("type") in ("Polygon", "MultiPolygon"):
                try:
                    ring = coords[0] if geom["type"] == "Polygon" else coords[0][0]
                    lon = sum(c[0] for c in ring) / len(ring)
                    lat = sum(c[1] for c in ring) / len(ring)
                    coords = [lon, lat]
                except (IndexError, TypeError, ZeroDivisionError):
                    coords = [-2.0, 53.0]

            observations.append({
                "obs_type": "economic",
                "timestamp": datetime.now(),
                "geometry": {
                    "type": "Point",
                    "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else [-2.0, 53.0],
                },
                "source_id": f"ce-{layer}-{props.get('Name') or props.get('OBJECTID', len(observations))}",
                "source_name": "Crown Estate UK",
                "quality_score": 0.95,
                "payload": {
                    "layer": layer,
                    "name": props.get("Name") or props.get("name") or props.get("Site_Name", ""),
                    "operator": props.get("Operator") or props.get("Developer", ""),
                    "status": props.get("Status") or props.get("status", ""),
                    "capacity_mw": props.get("Capacity_MW") or props.get("Capacity_") or props.get("capacity"),
                    "turbines": props.get("No_Turbines") or props.get("Turbines"),
                    "round": props.get("Round") or props.get("Leasing_Round", ""),
                    "area_km2": props.get("Area_km2") or props.get("area"),
                    "water_depth_m": props.get("Water_Depth") or props.get("Depth"),
                    "distance_shore_km": props.get("Distance_Shore") or props.get("Shore_Dist"),
                },
            })

        logger.info("Crown Estate %s returned %d features", layer, len(observations))
        return observations
