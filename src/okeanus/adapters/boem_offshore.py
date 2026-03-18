"""BOEM (Bureau of Ocean Energy Management) offshore energy leases adapter.

US offshore wind energy lease areas, oil/gas lease blocks,
and renewable energy project data on the Outer Continental Shelf.

API: GeoJSON/ArcGIS REST at gis.boem.gov.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://gis.boem.gov/arcgis/rest/services"

# Key BOEM feature services
LAYERS = {
    "wind_leases": "https://services7.arcgis.com/G5Ma95RzqJRPKsWL/arcgis/rest/services/Wind_Leases__BOEM_/FeatureServer/0",
    "wind_planning": f"{BASE_URL}/BOEM_BSEE/Wind_Planning_Areas/MapServer/0",
    "oil_gas_leases": f"{BASE_URL}/BOEM_BSEE/Active_Leases/MapServer/0",
    "platforms": f"{BASE_URL}/BOEM_BSEE/Platform_Structures/MapServer/0",
    "pipelines": f"{BASE_URL}/BOEM_BSEE/Pipeline_Routes/MapServer/0",
}


class BoemOffshoreAdapter(BaseAdapter):
    """Connector for BOEM — US offshore energy leases/infrastructure (no auth).

    Returns offshore wind lease areas, oil/gas blocks, platforms,
    and pipeline routes on the US OCS.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "boem_offshore"

    @property
    def source_url(self) -> str:
        return "https://www.boem.gov/"

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
        """Fetch BOEM offshore energy data.

        Extra params:
            layer: 'wind_leases' (default), 'wind_planning', 'oil_gas_leases', 'platforms', 'pipelines'
            limit: max features (default: 200)
        """
        layer = params.get("layer", "wind_leases")
        limit = params.get("limit", 200)

        url = LAYERS.get(layer, LAYERS["wind_leases"])
        w, s, e, n = bbox

        query: dict[str, Any] = {
            "where": "1=1",
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
            logger.error("BOEM fetch %s failed: %s", layer, exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            # Extract centroid for Point geometry
            coords = geom.get("coordinates", [0, 0])
            if geom.get("type") in ("Polygon", "MultiPolygon"):
                # Use first coordinate as approximate location
                try:
                    if geom["type"] == "Polygon":
                        ring = coords[0] if coords else []
                        lon = sum(c[0] for c in ring) / len(ring) if ring else 0
                        lat = sum(c[1] for c in ring) / len(ring) if ring else 0
                    else:
                        ring = coords[0][0] if coords and coords[0] else []
                        lon = sum(c[0] for c in ring) / len(ring) if ring else 0
                        lat = sum(c[1] for c in ring) / len(ring) if ring else 0
                    coords = [lon, lat]
                except (IndexError, TypeError, ZeroDivisionError):
                    coords = [0, 0]

            lease_date = props.get("LEASE_DATE") or props.get("lease_date") or ""
            try:
                if isinstance(lease_date, (int, float)) and lease_date > 1e10:
                    ts = datetime.fromtimestamp(lease_date / 1000)
                elif isinstance(lease_date, str) and lease_date:
                    # Try MM/DD/YYYY first, then YYYY-MM-DD
                    if "/" in lease_date:
                        ts = datetime.strptime(lease_date.strip(), "%m/%d/%Y")
                    else:
                        ts = datetime.strptime(lease_date[:10], "%Y-%m-%d")
                else:
                    ts = datetime.now()
            except (ValueError, TypeError, OSError):
                ts = datetime.now()

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else [0, 0],
                },
                "source_id": f"boem-{layer}-{props.get('LEASE_NUMBER') or props.get('OBJECTID', len(observations))}",
                "source_name": "BOEM",
                "quality_score": 0.95,
                "payload": {
                    "layer": layer,
                    "lease_number": props.get("LEASE_NUMBER") or props.get("Lease_Number", ""),
                    "company": props.get("COMPANY") or props.get("Company", ""),
                    "state": props.get("STATE") or props.get("State", ""),
                    "area_name": props.get("PROTRACTION_NAME") or props.get("AREA_NAME", ""),
                    "status": props.get("LEASE_STATUS") or props.get("Status", ""),
                    "capacity_mw": props.get("CAPACITY_MW") or props.get("Capacity"),
                    "acreage": props.get("LEASE_ACRES") or props.get("Acreage"),
                    "block": props.get("BLOCK_NUMBER") or props.get("Block", ""),
                    "effective_date": str(lease_date)[:10] if lease_date else "",
                    "original_geometry_type": geom.get("type", ""),
                },
            })

        logger.info("BOEM %s returned %d features", layer, len(observations))
        return observations
