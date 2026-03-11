"""EMODnet Bathymetry adapter — European seabed depth data.

EMODnet Bathymetry provides high-resolution gridded bathymetry for
European seas via WCS (Web Coverage Service) and WMS. No auth required.

Data portal: https://www.emodnet-bathymetry.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://ows.emodnet-bathymetry.eu/wms"
WCS_URL = "https://ows.emodnet-bathymetry.eu/wcs"


class EmodnetBathymetryAdapter(BaseAdapter):
    """Connector for EMODnet Bathymetry (no auth required).

    Queries the WCS endpoint for depth values and metadata within a bbox.
    For large areas, returns a sampled grid of depth points.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "emodnet_bathymetry"

    @property
    def source_url(self) -> str:
        return "https://www.emodnet-bathymetry.eu/"

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
        """Fetch bathymetry metadata for the specified bbox.

        Returns coverage description with depth statistics for the area.
        For individual depth points, use the WMS GetFeatureInfo endpoint.

        Extra params:
            resolution: grid resolution in degrees (default 0.1)
            limit: max sample points (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        resolution = params.get("resolution", 0.1)

        # Use GetFeatureInfo for point depth queries across a grid
        observations: list[dict[str, Any]] = []

        # Sample points across the bbox
        import math
        lon_steps = max(1, min(int((e - w) / resolution), int(math.sqrt(limit))))
        lat_steps = max(1, min(int((n - s) / resolution), limit // lon_steps))

        lon_step = (e - w) / lon_steps if lon_steps > 1 else 0
        lat_step = (n - s) / lat_steps if lat_steps > 1 else 0

        for i in range(lon_steps):
            for j in range(lat_steps):
                if len(observations) >= limit:
                    break

                lon = w + i * lon_step + lon_step / 2
                lat = s + j * lat_step + lat_step / 2

                gfi_params: dict[str, Any] = {
                    "service": "WMS",
                    "version": "1.3.0",
                    "request": "GetFeatureInfo",
                    "layers": "emodnet:mean",
                    "query_layers": "emodnet:mean",
                    "info_format": "application/json",
                    "crs": "EPSG:4326",
                    "bbox": f"{lat - 0.01},{lon - 0.01},{lat + 0.01},{lon + 0.01}",
                    "width": 2,
                    "height": 2,
                    "i": 1,
                    "j": 1,
                }

                try:
                    resp = await self._request("GET", BASE_URL, params=gfi_params)
                    data = resp.json()
                except Exception:
                    continue

                features = data.get("features", [])
                for feat in features:
                    props = feat.get("properties", {})
                    depth = props.get("GRAY_INDEX", props.get("value"))
                    if depth is not None:
                        observations.append({
                            "obs_type": "physical",
                            "timestamp": time_start,
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "source_id": f"emodnet-bathy-{lon:.4f}-{lat:.4f}",
                            "source_name": "EMODnet Bathymetry",
                            "quality_score": 0.9,
                            "payload": {
                                "depth_m": float(depth),
                                "source_resolution": "~115m (1/16 arc-minute)",
                                "datum": "MSL",
                            },
                        })
                        break

        logger.info("EMODnet Bathymetry returned %d depth points", len(observations))
        return observations
