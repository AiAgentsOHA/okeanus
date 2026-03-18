"""NCEI Marine Microplastics adapter — 1M+ global records via ArcGIS.

NOAA NCEI's marine microplastics data collection provides global open access
to marine microplastic data. Served via ArcGIS FeatureServer with GeoJSON
output. No auth required.

Source: https://www.ncei.noaa.gov/products/microplastics
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

FEATURE_URL = (
    "https://services2.arcgis.com/C8EMgrsFcRFL6LrL/arcgis/rest/services/"
    "Marine_Microplastics_WGS84/FeatureServer/0/query"
)


class NceiMicroplasticsAdapter(BaseAdapter):
    """Connector for NCEI Marine Microplastics (ArcGIS FeatureServer)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=30.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ncei_microplastics"

    @property
    def source_url(self) -> str:
        return "https://www.ncei.noaa.gov/products/microplastics"

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
        """Fetch marine microplastic sample records.

        Extra params:
            medium: Filter by sample medium ('Ocean water', 'Sediment', 'Beach')
            limit: Max records (default 100)
        """
        limit = min(params.get("limit", 100), 1000)
        medium_filter = params.get("medium", "")
        w, s, e, n = bbox

        # Build ArcGIS where clause
        where_parts = ["1=1"]
        if medium_filter:
            where_parts.append(f"Medium='{medium_filter}'")

        query_params: dict[str, Any] = {
            "where": " AND ".join(where_parts),
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "resultRecordCount": limit,
            "f": "geojson",
        }

        try:
            resp = await self._request("GET", FEATURE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("NCEI microplastics fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if len(observations) >= limit:
                break

            props = feat.get("properties", {})
            geom = feat.get("geometry")

            ts = datetime.now(timezone.utc)

            oid = props.get("OBJECTID", "")
            lat = props.get("Latitude__degree_")
            lon = props.get("Longitude_degree_")
            ocean = props.get("Location_Oceans", "")
            region = props.get("Location_Regions", "")
            country = props.get("Country", "")
            medium = props.get("Medium", "")
            method = props.get("Sampling_Method", "")
            mesh_mm = props.get("Mesh_size__mm_")

            observations.append({
                "obs_type": "microplastics",
                "timestamp": ts,
                "geometry": geom,
                "source_id": f"ncei-mp-{oid}",
                "source_name": "NCEI Marine Microplastics",
                "quality_score": 0.9,
                "payload": {
                    "object_id": oid,
                    "ocean": ocean,
                    "region": region,
                    "sub_region": props.get("Location_SubRegions", ""),
                    "country": country,
                    "beach_location": props.get("Beach_Location", ""),
                    "medium": medium,
                    "water_depth_m": props.get("Ocean_Bottom_Depth__m_", ""),
                    "sample_depth_m": props.get("Water_Sample_Depth__m_"),
                    "sampling_method": method,
                    "mesh_size_mm": mesh_mm,
                    "standardized_nurdle_amount": props.get(
                        "Standardized_Nurdle__Amount", ""
                    ),
                },
            })

        logger.info("NCEI microplastics returned %d records", len(observations))
        return observations
