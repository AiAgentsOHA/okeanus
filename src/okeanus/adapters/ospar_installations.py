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
WFS_URL = "https://odims.ospar.org/geoserver/ows"
WFS_LAYER = "odims:ospar_offshore_installations_2023_01_001"


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

        # Use OSPAR GeoServer WFS endpoint
        cql_parts: list[str] = []
        if status:
            cql_parts.append(f"Current_st='{status}'")
        if country:
            cql_parts.append(f"Country='{country}'")

        query: dict[str, Any] = {
            "service": "WFS",
            "version": "1.0.0",
            "request": "GetFeature",
            "typeName": WFS_LAYER,
            "outputFormat": "application/json",
            "maxFeatures": limit,
            "srsName": "EPSG:4326",
        }

        # WFS 1.0.0 uses lon,lat bbox order (matches our internal convention)
        if not (w <= -179 and s <= -89 and e >= 179 and n >= 89):
            query["BBOX"] = f"{w},{s},{e},{n}"

        if cql_parts:
            query["CQL_FILTER"] = " AND ".join(cql_parts)

        try:
            resp = await self._request("GET", WFS_URL, params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("OSPAR WFS failed: %s, trying API fallback", exc)
            return await self._fetch_api(bbox, status, country, limit)

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [0, 0])

            # WFS fields: ID, Country, Year, Name, Location, Latitude,
            # Longitude, Water_dept, Operator, Oper_st, Current_st,
            # Primary_hy, Category, Function, Weight_sub, Weight_top
            year_val = props.get("Year") or ""
            try:
                yr = int(year_val) if year_val else 0
                ts = datetime(yr, 1, 1) if yr > 1900 else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": coords if isinstance(coords, list) and len(coords) >= 2 else [0, 0],
                },
                "source_id": f"ospar-{props.get('ID') or props.get('Name') or len(observations)}",
                "source_name": "OSPAR",
                "quality_score": 0.93,
                "payload": {
                    "name": props.get("Name", ""),
                    "operator": props.get("Operator", ""),
                    "country": props.get("Country", ""),
                    "status": props.get("Current_st", ""),
                    "category": props.get("Category", ""),
                    "function": props.get("Function", ""),
                    "primary_hydrocarbon": props.get("Primary_hy", ""),
                    "location": props.get("Location", ""),
                    "water_depth_m": props.get("Water_dept"),
                    "weight_substructure": props.get("Weight_sub"),
                    "weight_topside": props.get("Weight_top"),
                    "year": yr if yr > 1900 else None,
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
