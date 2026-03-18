"""GEBCO adapter -- global ocean bathymetry via WMS.

GEBCO (General Bathymetric Chart of the Oceans) provides global gridded
bathymetry. This adapter queries depth values via the WMS GetFeatureInfo
endpoint. No authentication required.

Data portal: https://www.gebco.net/
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://wms.gebco.net/mapserv"

# Cap grid to 3x3 to avoid timeouts (each point = 1 WMS request)
MAX_GRID_DIM = 3


class GebcoAdapter(BaseAdapter):
    """Connector for GEBCO global bathymetry (no auth required).

    Queries the WMS GetFeatureInfo endpoint for depth values at grid
    points across the requested bounding box.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "gebco"

    @property
    def source_url(self) -> str:
        return "https://www.gebco.net/"

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
        """Fetch bathymetry depth points across the bbox from GEBCO WMS.

        Samples a grid of up to 10x10 points. Larger grids are clamped
        to avoid timeout.

        Extra params:
            grid_size: max points per axis (default 10, clamped to 10)
        """
        w, s, e, n = bbox
        grid_size = min(params.get("grid_size", MAX_GRID_DIM), MAX_GRID_DIM)

        lon_range = e - w
        lat_range = n - s

        lon_steps = max(1, min(grid_size, int(math.ceil(lon_range / 0.5))))
        lat_steps = max(1, min(grid_size, int(math.ceil(lat_range / 0.5))))

        lon_step = lon_range / lon_steps if lon_steps > 1 else 0
        lat_step = lat_range / lat_steps if lat_steps > 1 else 0

        observations: list[dict[str, Any]] = []

        for i in range(lon_steps):
            for j in range(lat_steps):
                lon = w + i * lon_step + lon_step / 2 if lon_steps > 1 else (w + e) / 2
                lat = s + j * lat_step + lat_step / 2 if lat_steps > 1 else (s + n) / 2

                # Build a tiny bbox around the point for GetFeatureInfo
                half = 0.005
                gfi_params: dict[str, Any] = {
                    "SERVICE": "WMS",
                    "VERSION": "1.3.0",
                    "REQUEST": "GetFeatureInfo",
                    "LAYERS": "GEBCO_LATEST_2",
                    "QUERY_LAYERS": "GEBCO_LATEST_2",
                    "INFO_FORMAT": "text/plain",
                    "CRS": "EPSG:4326",
                    "BBOX": f"{lat - half},{lon - half},{lat + half},{lon + half}",
                    "WIDTH": 2,
                    "HEIGHT": 2,
                    "I": 1,
                    "J": 1,
                }

                try:
                    resp = await self._request("GET", BASE_URL, params=gfi_params)
                    text = resp.text.strip()
                except Exception:
                    logger.debug("GEBCO query failed for (%.4f, %.4f)", lon, lat)
                    continue

                # Parse depth from plain text response
                # Typical response: "value_0 = -4523.0" or similar
                depth = self._parse_depth(text)
                if depth is None:
                    continue

                observations.append({
                    "obs_type": "physical",
                    "timestamp": time_start,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"gebco-{lon:.4f}-{lat:.4f}",
                    "source_name": "GEBCO",
                    "quality_score": 0.9,
                    "payload": {
                        "depth_m": depth,
                        "source_resolution": "15 arc-second",
                        "datum": "MSL",
                    },
                })

        logger.info("GEBCO returned %d depth points", len(observations))
        return observations

    @staticmethod
    def _parse_depth(text: str) -> float | None:
        """Extract a numeric depth value from WMS GetFeatureInfo text response."""
        for line in text.splitlines():
            line = line.strip()
            if "=" in line:
                _, _, value_part = line.partition("=")
                try:
                    return float(value_part.strip().strip("'\""))
                except ValueError:
                    continue
            # Try parsing the whole line as a number
            try:
                return float(line)
            except ValueError:
                continue
        return None
