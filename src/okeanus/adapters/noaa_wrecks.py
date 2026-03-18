"""NOAA Wrecks and Obstructions adapter.

~13,000 wrecks and obstructions in US waters from NOAA's
Electronic Navigational Charts (ENC). No auth required.

Data source: https://nauticalcharts.noaa.gov/data/wrecks-and-obstructions.html
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Primary: NOAA ENC Direct to GIS (wrecks layer 33)
BASE_URL = "https://encdirect.noaa.gov/arcgis/rest/services/encdirect/enc_coastal/MapServer/33/query"
# Fallback: obstructions layer 30
FALLBACK_URL = "https://encdirect.noaa.gov/arcgis/rest/services/encdirect/enc_coastal/MapServer/30/query"


class NoaaWrecksAdapter(BaseAdapter):
    """Connector for NOAA wrecks and obstructions via ArcGIS REST (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_wrecks"

    @property
    def source_url(self) -> str:
        return "https://nauticalcharts.noaa.gov/data/wrecks-and-obstructions.html"

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
        """Fetch wrecks and obstructions within bbox.

        Time range is largely ignored — wreck data is historical/static.

        Extra params:
            feature_type: 'wreck', 'obstruction', or 'all' (default)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        feature_type = params.get("feature_type", "all")

        where = "1=1"
        if feature_type == "wreck":
            where = "FEATURE_TYPE = 'Wreck'"
        elif feature_type == "obstruction":
            where = "FEATURE_TYPE = 'Obstruction'"

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
            if not data.get("features"):
                raise ValueError("No features from primary URL")
        except Exception:
            # Fallback to alternative service
            logger.warning("NOAA Wrecks primary URL failed, trying fallback")
            try:
                resp = await self._request("GET", FALLBACK_URL, params=api_params)
                data = resp.json()
            except Exception as exc:
                logger.error("NOAA Wrecks fetch failed (both URLs): %s", exc)
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

            # Use discovery/sinking year if available
            year = attrs.get("YEARSUNK") or attrs.get("YEARFOUND")
            try:
                ts = datetime(int(year), 1, 1) if year and str(year).isdigit() else datetime(1900, 1, 1)
            except (ValueError, TypeError):
                ts = datetime(1900, 1, 1)

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"noaa-wreck-{attrs.get('OBJECTID', attrs.get('RECRD', ''))}",
                "source_name": "NOAA Wrecks",
                "quality_score": 0.8,
                "payload": {
                    "feature_type": attrs.get("FEATURE_TYPE", ""),
                    "vessel_name": attrs.get("VESSLTERMS", ""),
                    "history": attrs.get("HISTORY", ""),
                    "chart_number": attrs.get("CHART", ""),
                    "depth_m": attrs.get("DEPTH"),
                    "sounding_type": attrs.get("SOUNDING_TYPE", ""),
                    "condition": attrs.get("CONDITION", ""),
                    "gp_quality": attrs.get("GP_QUALITY", ""),
                    "year_sunk": attrs.get("YEARSUNK"),
                    "quasou": attrs.get("QUASOU", ""),
                },
            })

        logger.info("NOAA Wrecks returned %d features", len(observations))
        return observations
