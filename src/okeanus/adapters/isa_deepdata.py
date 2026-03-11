"""ISA DeepData adapter — International Seabed Authority.

Seabed mining exploration contracts, environmental baselines,
and mineral resource data from the deep ocean floor.

API: Spatial portal at data.isa.org.jm.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://data.isa.org.jm/isa/rest/services"
GEOSERVER_URL = "https://gis.isa.org.jm/geoserver/isa/ows"


class IsaDeepDataAdapter(BaseAdapter):
    """Connector for ISA DeepData — seabed mining contracts (no auth).

    Returns data on deep-sea mining exploration contracts,
    contractor information, mineral resources, and environmental baselines.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "isa_deepdata"

    @property
    def source_url(self) -> str:
        return "https://data.isa.org.jm/"

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
        """Fetch ISA seabed mining data.

        Extra params:
            layer: 'contracts' (default), 'reserved_areas', 'environmental'
            mineral: 'polymetallic_nodules', 'sulphides', 'crusts'
            limit: max features (default: 100)
        """
        layer = params.get("layer", "contracts")
        mineral = params.get("mineral")
        limit = params.get("limit", 100)

        w, s, e, n = bbox

        # Try GeoServer WFS endpoint
        type_name = f"isa:{layer}"
        query: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeName": type_name,
            "outputFormat": "application/json",
            "count": limit,
            "srsName": "EPSG:4326",
        }

        if w != 0 or s != 0 or e != 0 or n != 0:
            query["BBOX"] = f"{s},{w},{n},{e},EPSG:4326"

        cql_filters = []
        if mineral:
            cql_filters.append(f"mineral_type='{mineral}'")
        if cql_filters:
            query["CQL_FILTER"] = " AND ".join(cql_filters)

        try:
            resp = await self._request("GET", GEOSERVER_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("ISA GeoServer failed: %s, trying ArcGIS", exc)
            return await self._fetch_arcgis(bbox, layer, limit)

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
                    coords = [-140, -10]

            contract_date = props.get("contract_date") or props.get("date_signed") or ""
            try:
                ts = datetime.strptime(contract_date[:10], "%Y-%m-%d") if contract_date else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else [-140, -10],
                },
                "source_id": f"isa-{layer}-{props.get('contract_id') or props.get('id', len(observations))}",
                "source_name": "ISA DeepData",
                "quality_score": 0.93,
                "payload": {
                    "layer": layer,
                    "contractor": props.get("contractor") or props.get("Contractor", ""),
                    "sponsoring_state": props.get("sponsoring_state") or props.get("State", ""),
                    "mineral_type": props.get("mineral_type") or props.get("Mineral", ""),
                    "area_name": props.get("area_name") or props.get("Area", ""),
                    "area_km2": props.get("area_km2") or props.get("Area_sqkm"),
                    "contract_date": contract_date,
                    "expiry_date": props.get("expiry_date") or props.get("Expiry", ""),
                    "status": props.get("status") or props.get("Status", ""),
                    "ocean_region": props.get("ocean_region") or props.get("Region", ""),
                },
            })

        logger.info("ISA DeepData %s returned %d features", layer, len(observations))
        return observations

    async def _fetch_arcgis(
        self,
        bbox: tuple[float, float, float, float],
        layer: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: try ISA ArcGIS REST endpoint."""
        url = f"{BASE_URL}/ISA_Areas/MapServer/0/query"
        w, s, e, n = bbox

        query: dict[str, Any] = {
            "where": "1=1",
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultRecordCount": limit,
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("ISA ArcGIS fallback failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue
            props = feat.get("properties", {})
            observations.append({
                "obs_type": "economic",
                "timestamp": datetime.now(),
                "geometry": feat.get("geometry", {"type": "Point", "coordinates": [-140, -10]}),
                "source_id": f"isa-arcgis-{len(observations)}",
                "source_name": "ISA DeepData",
                "quality_score": 0.85,
                "payload": {"layer": layer, **props},
            })

        return observations
