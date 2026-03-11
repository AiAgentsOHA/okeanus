"""NOAA ERMA adapter — Environmental Response Management Application.

NOAA's ERMA provides geospatial data for environmental incidents including
oil spills, chemical releases, and natural hazards. Accessed via ArcGIS
REST Feature Service. No auth required.

Data source: https://erma.noaa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = (
    "https://gis.response.restoration.noaa.gov/arcgis/rest/services"
    "/ERMA_Public/MapServer/0/query"
)


class NoaaErmaAdapter(BaseAdapter):
    """Connector for NOAA ERMA ArcGIS REST endpoint (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_erma"

    @property
    def source_url(self) -> str:
        return "https://erma.noaa.gov/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch environmental incident data within bbox.

        Extra params:
            incident_type: filter by type (e.g. 'Oil', 'Chemical')
            limit: max records to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        incident_type = params.get("incident_type")

        where = "1=1"
        if incident_type:
            where = f"IncidentType = '{incident_type}'"

        api_params: dict[str, Any] = {
            "where": where,
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
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA ERMA fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            geom = feat.get("geometry", {})
            attrs = feat.get("attributes", {})

            lon = geom.get("x")
            lat = geom.get("y")
            if lon is None or lat is None:
                continue

            # Parse epoch timestamp
            ts_raw = attrs.get("IncidentDate") or attrs.get("OpenDate")
            if ts_raw and isinstance(ts_raw, (int, float)):
                try:
                    ts = datetime.fromtimestamp(ts_raw / 1000)
                except (ValueError, OSError):
                    ts = time_start
            else:
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"erma-{attrs.get('OBJECTID', '')}",
                "source_name": "NOAA ERMA",
                "quality_score": 0.85,
                "payload": {
                    "incident_name": attrs.get("IncidentName", attrs.get("Name", "")),
                    "incident_type": attrs.get("IncidentType", ""),
                    "status": attrs.get("Status", ""),
                    "description": attrs.get("Description", ""),
                    "open_date": attrs.get("OpenDate"),
                    "close_date": attrs.get("CloseDate"),
                    "responsible_party": attrs.get("ResponsibleParty", ""),
                    "state": attrs.get("State", ""),
                },
            })

        logger.info("NOAA ERMA returned %d incidents", len(observations))
        return observations
