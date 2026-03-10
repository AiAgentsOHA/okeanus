"""BOEM Offshore Wind Energy Areas adapter.

Bureau of Ocean Energy Management (BOEM) offshore wind lease areas and
planning areas in US federal waters. No auth required.

Data source: https://www.boem.gov/renewable-energy/mapping-and-data
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://gis.boem.gov/arcgis/rest/services/BOEMWindEnergyAreas/MapServer/0/query"


class BoemWindAdapter(BaseAdapter):
    """Connector for BOEM Offshore Wind Energy Areas via ArcGIS REST (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "boem_wind"

    @property
    def source_url(self) -> str:
        return "https://www.boem.gov/renewable-energy/mapping-and-data"

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
        """Fetch offshore wind energy areas within bbox.

        Extra params:
            state: filter by state (e.g. 'New Jersey')
            status: filter by lease status (e.g. 'Active')
            category: filter by category (e.g. 'Lease Area')
            limit: max records to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        state = params.get("state")
        status = params.get("status")
        category = params.get("category")

        clauses: list[str] = []
        if state:
            clauses.append(f"STATE = '{state}'")
        if status:
            clauses.append(f"LEASE_STATUS = '{status}'")
        if category:
            clauses.append(f"CATEGORY1 = '{category}'")
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
            logger.error("BOEM Wind fetch failed: %s", exc)
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

            raw_date = attrs.get("LEASE_DATE")
            try:
                if isinstance(raw_date, (int, float)) and raw_date > 1e10:
                    ts = datetime.utcfromtimestamp(raw_date / 1000)
                else:
                    ts = datetime(1900, 1, 1)
            except (ValueError, TypeError, OSError):
                ts = datetime(1900, 1, 1)

            observations.append({
                "obs_type": "regulatory",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"boem-wind-{attrs.get('LEASE_NUMBER', attrs.get('OBJECTID', ''))}",
                "source_name": "BOEM Offshore Wind",
                "quality_score": 0.9,
                "payload": {
                    "lease_number": attrs.get("LEASE_NUMBER", ""),
                    "company": attrs.get("COMPANY", ""),
                    "state": attrs.get("STATE", ""),
                    "area_name": attrs.get("LEASE_AREA_NAME", attrs.get("PROTRACTION_NAME", "")),
                    "status": attrs.get("LEASE_STATUS", ""),
                    "area_sq_km": attrs.get("AREA_SQ_KM", attrs.get("Shape_Area")),
                    "lease_date": attrs.get("LEASE_DATE"),
                    "category": attrs.get("CATEGORY1", ""),
                },
            })

        logger.info("BOEM Wind returned %d features", len(observations))
        return observations
