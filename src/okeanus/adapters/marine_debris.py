"""Marine Debris adapter — NOAA Marine Microplastics data.

Global marine microplastics observations from NOAA's National Centers for
Environmental Information (NCEI), served via ArcGIS FeatureServer.
Includes concentration measurements, sampling methods, and scientific
references. No auth required.

Note: The original NOAA MDMAP API (marinedebris.noaa.gov/mdmap/api) was
decommissioned / blocked behind a WAF as of early 2025. This adapter now
uses the NOAA Marine Microplastics WGS84 ArcGIS feature service which
provides peer-reviewed microplastics survey data worldwide.

Data portal: https://www.ncei.noaa.gov/products/microplastics
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# NOAA Marine Microplastics ArcGIS FeatureServer
ARCGIS_URL = (
    "https://services2.arcgis.com/C8EMgrsFcRFL6LrL/ArcGIS/rest/services"
    "/Marine_Microplastics_WGS84/FeatureServer/0/query"
)


class MarineDebrisAdapter(BaseAdapter):
    """Connector for NOAA Marine Microplastics data (no auth required).

    Uses ArcGIS FeatureServer for global microplastics survey observations.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=45.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "marine_debris"

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
        """Fetch marine microplastics observations within bbox.

        Extra params:
            medium: Filter by medium (e.g. 'Ocean water', 'Beach sand')
            limit: Max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        medium = params.get("medium", "")

        # Build ArcGIS query
        where_clause = "1=1"
        if medium:
            where_clause = f"Medium = '{medium}'"

        # Convert time range to epoch milliseconds for date filtering
        ts_start_ms = int(time_start.timestamp() * 1000)
        ts_end_ms = int(time_end.timestamp() * 1000)

        # Add date filter if the field has data
        date_where = (
            f"Date_m_d_yyyy >= {ts_start_ms} AND Date_m_d_yyyy <= {ts_end_ms}"
        )
        if where_clause == "1=1":
            where_clause = date_where
        else:
            where_clause = f"({where_clause}) AND ({date_where})"

        api_params: dict[str, Any] = {
            "where": where_clause,
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": limit,
            "f": "json",
        }

        try:
            resp = await self._request("GET", ARCGIS_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Marine Debris (Microplastics) fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        if not features:
            # Retry without date filter -- many records lack date values
            api_params["where"] = "1=1" if not medium else f"Medium = '{medium}'"
            try:
                resp = await self._request("GET", ARCGIS_URL, params=api_params)
                data = resp.json()
                features = data.get("features", [])
            except Exception:
                pass

        observations: list[dict[str, Any]] = []

        for feat in features:
            attrs = feat.get("attributes", {})
            geom = feat.get("geometry", {})

            lon = geom.get("x", attrs.get("Longitude_degree_"))
            lat = geom.get("y", attrs.get("Latitude__degree_"))
            if lon is None or lat is None:
                continue

            # Parse epoch-millisecond timestamp
            date_ms = attrs.get("Date_m_d_yyyy")
            if date_ms and isinstance(date_ms, (int, float)):
                ts = datetime.fromtimestamp(date_ms / 1000, tz=timezone.utc)
            else:
                ts = datetime.now(timezone.utc)

            obj_id = attrs.get("OBJECTID", attrs.get("GlobalID", ""))

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"microplastics-{obj_id}",
                "source_name": "NOAA Marine Microplastics",
                "quality_score": 0.85,
                "payload": {
                    "medium": attrs.get("Medium", ""),
                    "location_ocean": attrs.get("Location_Oceans", ""),
                    "location_region": attrs.get("Location_Regions", ""),
                    "country": attrs.get("Country", ""),
                    "beach_location": attrs.get("Beach_Location", ""),
                    "sampling_method": attrs.get("Sampling_Method", ""),
                    "mesh_size_mm": attrs.get("Mesh_size__mm_"),
                    "measurement": attrs.get("Microplastics_measurement"),
                    "unit": attrs.get("Unit", ""),
                    "concentration_class": attrs.get("Concentration_class_text", ""),
                    "concentration_range": attrs.get("Concentration_class_range", ""),
                    "water_depth_m": attrs.get("Water_Sample_Depth__m_"),
                    "sediment_depth_m": attrs.get("Sediment_Sample_Depth__m_"),
                    "organization": attrs.get("ORGANIZATION", ""),
                    "reference": attrs.get("Short_Reference", ""),
                    "doi": attrs.get("DOI", ""),
                    "ncei_accession": attrs.get("NCEI_Accession_No"),
                },
            })

        logger.info("Marine Debris (Microplastics) returned %d observations", len(observations))
        return observations
