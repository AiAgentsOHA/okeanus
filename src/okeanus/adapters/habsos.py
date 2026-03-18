"""NOAA HABSOS adapter — Harmful Algal BloomS Observing System.

HAB cell counts and species observations along US coastal waters.
No auth required.  Uses the NCEI ArcGIS map service for HABSOS data.

Data portal: https://habsos.noaa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# HABSOS cell count data served via NCDC ArcGIS MapServer.
# Multiple URL patterns — NCEI has restructured endpoints historically.
_ARCGIS_URLS = [
    (
        "https://gis.ncdc.noaa.gov/arcgis/rest/services"
        "/ms/HABSOS_CellCounts/MapServer/0/query"
    ),
    (
        "https://gis.ncdc.noaa.gov/arcgis/rest/services"
        "/ms/HABSOS_CellCounts/MapServer/1/query"
    ),
]


class HabsosAdapter(BaseAdapter):
    """Connector for NOAA HABSOS HAB cell count observations."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "habsos"

    @property
    def source_url(self) -> str:
        return "https://habsos.noaa.gov/"

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch HAB cell count observations within bbox and time range.

        Extra params:
            species: Species name filter (e.g. 'Karenia brevis')
            state: US state filter (e.g. 'FL', 'TX')
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        # Clamp global bbox to Gulf of Mexico where HABSOS data exists
        if (e - w) > 100 or (n - s) > 100:
            w, s, e, n = -98.0, 24.0, -80.0, 31.0

        where_parts: list[str] = []
        if species := params.get("species"):
            where_parts.append(f"GENUS = '{species.split()[0]}'" if " " in species else f"GENUS = '{species}'")
        if state := params.get("state"):
            where_parts.append(f"STATE_ID = '{state}'")
        where = " AND ".join(where_parts) if where_parts else "1=1"

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

        # Try multiple ArcGIS endpoint URLs — NCEI restructures layers
        data: dict[str, Any] = {}
        for arcgis_url in _ARCGIS_URLS:
            try:
                resp = await self._request("GET", arcgis_url, params=api_params)
                data = resp.json()
                if data.get("features") or "error" not in data:
                    break
            except Exception as exc:
                logger.debug("HABSOS endpoint %s failed: %s", arcgis_url, exc)

        if "error" in data:
            logger.error("HABSOS ArcGIS service unavailable: %s", data["error"])
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

            raw_date = attrs.get("SAMPLE_DATE") or attrs.get("sampleDate")
            try:
                if isinstance(raw_date, (int, float)) and abs(raw_date) > 1e10:
                    ts = datetime.utcfromtimestamp(raw_date / 1000)
                elif raw_date:
                    ts = datetime.fromisoformat(str(raw_date).replace("Z", "+00:00"))
                else:
                    ts = time_start
            except (ValueError, TypeError, OSError):
                ts = time_start

            cell_count = attrs.get("CELLCOUNT", attrs.get("cellCount"))

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"habsos-{attrs.get('OBJECTID', attrs.get('ID', len(observations)))}",
                "source_name": "HABSOS",
                "quality_score": 0.9,
                "payload": {
                    "species": (
                        (attrs.get("GENUS", "") or "") + " " +
                        (attrs.get("SPECIES", "") or "")
                    ).strip(),
                    "cell_count_per_l": cell_count,
                    "category": attrs.get("CATEGORY", ""),
                    "state": attrs.get("STATE_ID", ""),
                    "description": attrs.get("DESCRIPTION", ""),
                    "sample_depth_m": attrs.get("SAMPLE_DEPTH"),
                    "water_temp_c": attrs.get("WATER_TEMP"),
                    "salinity_psu": attrs.get("SALINITY"),
                },
            })

        logger.info("HABSOS returned %d observations", len(observations))
        return observations
