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

ARCGIS_URL = "https://data.isa.org.jm/isa/map/arcgis/rest/services/ISAMapService/MapServer"


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

        # ArcGIS MapServer layers (confirmed from live service):
        #   0: V_FCLSTATIONP_CTD   — CTD station points
        #   1: V_FCLSTATIONP       — sampling stations (environmental data)
        #   2: fclSampleP          — sample points
        #   4: fclContractAreasBlocks — contract area polygons
        #   5: fclContractAreasCells  — contract area cells
        layer_id = {"contracts": 4, "stations": 1, "environmental": 0, "samples": 2}.get(layer, 1)
        url = f"{ARCGIS_URL}/{layer_id}/query"

        query: dict[str, Any] = {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
            "resultRecordCount": limit,
        }

        if not (w <= -179 and s <= -89 and e >= 179 and n >= 89):
            query["geometry"] = f"{w},{s},{e},{n}"
            query["geometryType"] = "esriGeometryEnvelope"
            query["inSR"] = "4326"
            query["outSR"] = "4326"
            query["spatialRel"] = "esriSpatialRelIntersects"

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("ISA DeepData ArcGIS fetch failed: %s — ISA data portal may be unavailable", exc)
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
                    coords = [-140, -10]

            # ActivityDate is epoch-ms in contract layers; stations lack dates
            activity_ms = props.get("ActivityDate")
            contract_date = props.get("contract_date") or props.get("date_signed") or ""
            try:
                if activity_ms and isinstance(activity_ms, (int, float)):
                    ts = datetime.utcfromtimestamp(activity_ms / 1000)
                elif contract_date:
                    ts = datetime.strptime(contract_date[:10], "%Y-%m-%d")
                else:
                    ts = datetime.now()
            except (ValueError, TypeError, OSError):
                ts = datetime.now()

            obj_id = props.get("OBJECTID") or props.get("contract_id") or props.get("id", len(observations))
            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else [-140, -10],
                },
                "source_id": f"isa-{layer}-{obj_id}",
                "source_name": "ISA DeepData",
                "quality_score": 0.93,
                "payload": {
                    "layer": layer,
                    "contractor": props.get("Contractor") or props.get("contractor", ""),
                    "contractor_id": props.get("ContractorID", ""),
                    "sponsoring_state": props.get("SponsoringState") or props.get("sponsoring_state", ""),
                    "contract_type": props.get("ContractType", ""),
                    "contract_status": props.get("ContractStatus") or props.get("Status", ""),
                    "area_key": props.get("AreaKey", ""),
                    "area_sector": props.get("AreaSector") or props.get("ocean_region", ""),
                    "area_km2": props.get("AreaKM2") or props.get("area_km2"),
                    "station_id": props.get("StationID", ""),
                    "status": props.get("Status") or props.get("ContractStatus", ""),
                },
            })

        logger.info("ISA DeepData %s returned %d features", layer, len(observations))
        return observations

