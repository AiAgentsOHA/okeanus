"""EMODnet Seabed Habitats adapter — EU seabed habitat classifications.

European Marine Observation and Data Network Seabed Habitats provides
classified seabed habitat maps across European seas via WFS.
No auth required.

Data portal: https://www.emodnet-seabedhabitats.eu/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://ows.emodnet-seabedhabitats.eu/geoserver/emodnet_open/wfs"

# Primary layer name — the most current known layer
_PRIMARY_LAYER = "emodnet_open:eusm2025_eunis2019_full"


class EmodnetSeabedAdapter(BaseAdapter):
    """Connector for EMODnet Seabed Habitats WFS endpoint (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        # Tight timeout: the EMODnet WFS server is often very slow or down.
        # We fail fast rather than hang for 90s.
        super().__init__(requests_per_second=1.0, timeout=25.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "emodnet_seabed"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """Fetch seabed habitat classifications within bbox.

        Extra params:
            habitat_type: EUNIS habitat code filter (e.g. 'A5.13')
            limit: Max features to return (default 20)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 20)

        # Shrink bbox to max 2x2 degrees — polygon features are large
        mid_lon, mid_lat = (w + e) / 2, (s + n) / 2
        half = 1.0
        w = max(w, mid_lon - half)
        e = min(e, mid_lon + half)
        s = max(s, mid_lat - half)
        n = min(n, mid_lat + half)

        habitat_type = params.get("habitat_type")

        # Quick connectivity check: test if the server responds at all
        # with a minimal WFS request before sending the real query.
        try:
            probe_params = {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": _PRIMARY_LAYER,
                "outputFormat": "application/json",
                "count": 1,
                "bbox": f"{mid_lat-0.01},{mid_lon-0.01},{mid_lat+0.01},{mid_lon+0.01},urn:ogc:def:crs:EPSG::4326",
            }
            await asyncio.wait_for(
                self._request("GET", BASE_URL, params=probe_params),
                timeout=15.0,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("EMODnet Seabed server unresponsive (probe failed): %s", exc)
            return []

        # Server is alive — send the real query
        api_params: dict[str, Any] = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": _PRIMARY_LAYER,
            "outputFormat": "application/json",
            "count": limit,
            "bbox": f"{s},{w},{n},{e},urn:ogc:def:crs:EPSG::4326",
        }
        if habitat_type:
            api_params["cql_filter"] = f"eunis2019c LIKE '{habitat_type}%'"

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("EMODnet Seabed Habitats fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry")

            if geom and geom.get("type") == "Point":
                coords = geom.get("coordinates", [])
                if len(coords) >= 2:
                    lon, lat = coords[0], coords[1]
                else:
                    continue
            elif geom and geom.get("type") in ("Polygon", "MultiPolygon"):
                # Use centroid of first polygon ring
                coords = geom.get("coordinates", [])
                if geom["type"] == "MultiPolygon" and coords:
                    ring = coords[0][0] if coords[0] else []
                elif coords:
                    ring = coords[0]
                else:
                    continue
                if ring:
                    lon = sum(pt[0] for pt in ring) / len(ring)
                    lat = sum(pt[1] for pt in ring) / len(ring)
                else:
                    continue
            else:
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"emodnet-seabed-{props.get('objectid', '')}",
                "source_name": "EMODnet Seabed Habitats",
                "quality_score": 0.85,
                "payload": {
                    "eunis_code": props.get("eunis2019c", ""),
                    "eunis_name": props.get("eunis2019d", ""),
                    "substrate": props.get("substrate", ""),
                    "biological_zone": props.get("biozone", ""),
                    "energy_level": props.get("energy", ""),
                    "salinity": props.get("salinity", ""),
                    "oxygen": props.get("oxygen", ""),
                },
            })

        logger.info("EMODnet Seabed Habitats returned %d features", len(observations))
        return observations
