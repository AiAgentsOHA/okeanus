"""OSPAR offshore installations adapter.

All NE Atlantic offshore oil/gas installations — location, operator,
status, decommissioning data.

Data: Shapefile/CSV download from OSPAR Data & Information Management System.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://odims.ospar.org/api/v1"
ARCGIS_URL = "https://odims.ospar.org/arcgis/rest/services/OSPAR/Offshore_Installations/MapServer/0"


class OsparInstallationsAdapter(BaseAdapter):
    """Connector for OSPAR — NE Atlantic offshore installations (no auth).

    Returns offshore oil/gas installation data including coordinates,
    operators, status, and decommissioning information.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ospar_installations"

    @property
    def source_url(self) -> str:
        return "https://odims.ospar.org/"

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
        """Fetch OSPAR offshore installations.

        Extra params:
            status: 'Operational', 'Decommissioned', etc.
            country: contracting party (e.g. 'United Kingdom', 'Norway')
            limit: max features (default: 500)
        """
        status = params.get("status")
        country = params.get("country")
        limit = params.get("limit", 500)

        w, s, e, n = bbox

        # Try ArcGIS REST endpoint
        where_parts = ["1=1"]
        if status:
            where_parts = [f"Status = '{status}'"]
        if country:
            where_parts.append(f"Country = '{country}'")

        query: dict[str, Any] = {
            "where": " AND ".join(where_parts),
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
            resp = await self._request("GET", f"{ARCGIS_URL}/query", params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("OSPAR ArcGIS failed: %s, trying API", exc)
            return await self._fetch_api(bbox, status, country, limit)

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])

            install_date = props.get("InstallDate") or props.get("Year_Installed") or ""
            try:
                if isinstance(install_date, (int, float)):
                    yr = int(install_date)
                    ts = datetime(yr, 1, 1) if yr > 1900 else datetime.now()
                elif isinstance(install_date, str) and install_date:
                    ts = datetime.strptime(install_date[:10], "%Y-%m-%d")
                else:
                    ts = datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else [0, 0],
                },
                "source_id": f"ospar-{props.get('Name') or props.get('OBJECTID', len(observations))}",
                "source_name": "OSPAR",
                "quality_score": 0.93,
                "payload": {
                    "name": props.get("Name") or props.get("Installation_Name", ""),
                    "operator": props.get("Operator") or props.get("operator", ""),
                    "country": props.get("Country") or props.get("country", ""),
                    "status": props.get("Status") or props.get("status", ""),
                    "type": props.get("Type") or props.get("Installation_Type", ""),
                    "field_name": props.get("Field") or props.get("Field_Name", ""),
                    "water_depth_m": props.get("Water_Depth") or props.get("Depth"),
                    "year_installed": props.get("Year_Installed"),
                    "year_decommissioned": props.get("Year_Decommissioned"),
                    "weight_tonnes": props.get("Weight") or props.get("Topside_Weight"),
                },
            })

        logger.info("OSPAR returned %d installations", len(observations))
        return observations

    async def _fetch_api(
        self,
        bbox: tuple[float, float, float, float],
        status: str | None,
        country: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: try OSPAR ODIMS API."""
        url = f"{BASE_URL}/layers/offshore_installations"
        query: dict[str, Any] = {"format": "json", "limit": limit}

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("OSPAR API fallback failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("features", data.get("data", []))
        observations: list[dict[str, Any]] = []

        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue
            props = rec.get("properties", rec)
            observations.append({
                "obs_type": "economic",
                "timestamp": datetime.now(),
                "geometry": rec.get("geometry", {"type": "Point", "coordinates": [0, 0]}),
                "source_id": f"ospar-api-{len(observations)}",
                "source_name": "OSPAR",
                "quality_score": 0.85,
                "payload": props,
            })

        return observations
