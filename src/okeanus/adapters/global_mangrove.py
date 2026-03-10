"""Global Mangrove Watch (GMW) adapter.

Mangrove extent, loss, and gain data from the Global Mangrove Watch
initiative, a collaboration between JAXA, Aberystwyth University, and
soloEO. No auth required.

Data source: https://www.globalmangrovewatch.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://services.arcgis.com/LBbVDC0hKPAnLRpO/arcgis/rest/services"
    "/GMW_v3/FeatureServer/0/query"
)


class GlobalMangroveAdapter(BaseAdapter):
    """Connector for Global Mangrove Watch (GMW) via ArcGIS REST (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "global_mangrove"

    @property
    def source_url(self) -> str:
        return "https://www.globalmangrovewatch.org/"

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
        """Fetch mangrove extent polygons within bbox.

        Extra params:
            country: filter by country name
            year: filter by mapping year (e.g. 2020)
            change_type: filter by change type (e.g. 'loss', 'gain')
            limit: max records to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        country = params.get("country")
        year = params.get("year")
        change_type = params.get("change_type")

        clauses: list[str] = []
        if country:
            clauses.append(f"Country = '{country}'")
        if year is not None:
            clauses.append(f"Year = {year}")
        if change_type:
            clauses.append(f"ChangeType = '{change_type}'")
        where = " AND ".join(clauses) if clauses else "1=1"

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
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Global Mangrove Watch fetch failed: %s", exc)
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

            map_year = attrs.get("Year")
            try:
                ts = datetime(int(map_year), 1, 1) if map_year else datetime(1900, 1, 1)
            except (ValueError, TypeError):
                ts = datetime(1900, 1, 1)

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"gmw-{attrs.get('OBJECTID', '')}",
                "source_name": "Global Mangrove Watch",
                "quality_score": 0.8,
                "payload": {
                    "area_ha": attrs.get("Area_ha", attrs.get("Shape_Area")),
                    "year": attrs.get("Year"),
                    "country": attrs.get("Country", ""),
                    "region": attrs.get("Region", ""),
                    "change_type": attrs.get("ChangeType", ""),
                    "coastline_km": attrs.get("Coastline_km"),
                },
            })

        logger.info("Global Mangrove Watch returned %d features", len(observations))
        return observations
