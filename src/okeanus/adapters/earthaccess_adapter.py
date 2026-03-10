"""NASA Earthdata adapter — satellite data via earthaccess.

Access to NASA's Earthdata catalog including PACE (hyperspectral ocean
color), MODIS, NSIDC (sea ice), and thousands of other datasets.

Requires:  pip install earthaccess
Auth:      NASA Earthdata login (free at urs.earthdata.nasa.gov)
Docs:      https://earthaccess.readthedocs.io/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Key NASA ocean datasets (short_name → description)
OCEAN_DATASETS = {
    "MUR-JPL-L4-GLOB-v4.1": "MUR SST (0.01 deg global)",
    "PACE_OCI_L2_AOP_NRT": "PACE ocean color (hyperspectral)",
    "MODIS_A-JPL-L2P-v2019.0": "MODIS Aqua SST L2",
    "NSIDC-0051": "Sea ice concentration (SMMR/SSM/I)",
    "NSIDC-0081": "Near-real-time sea ice concentration",
    "SWOT_L2_LR_SSH_2.0": "SWOT sea surface height",
    "CYGNSS_L2_V3.1": "CYGNSS ocean surface wind speed",
}


class EarthaccessAdapter(BaseAdapter):
    """Connector for NASA Earthdata via earthaccess (NASA login required)."""

    def __init__(self, *, username: str = "", password: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=120.0, **kwargs)
        self._username = username
        self._password = password

    @property
    def source_name(self) -> str:
        return "earthaccess"

    @property
    def source_url(self) -> str:
        return "https://search.earthdata.nasa.gov/"

    @property
    def update_frequency(self) -> str:
        return "varies"

    def _search_sync(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        short_name: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Synchronous earthaccess granule search — runs in executor."""
        try:
            import earthaccess
        except ImportError:
            logger.error("earthaccess not installed: pip install earthaccess")
            return []

        w, s, e, n = bbox

        # Authenticate if credentials provided
        if self._username and self._password:
            try:
                earthaccess.login(
                    strategy="environment",
                )
            except Exception:
                try:
                    earthaccess.login(
                        credentials={
                            "username": self._username,
                            "password": self._password,
                        },
                    )
                except Exception as exc:
                    logger.warning("NASA Earthdata login failed: %s", exc)

        try:
            results = earthaccess.search_data(
                short_name=short_name,
                bounding_box=(w, s, e, n),
                temporal=(
                    time_start.strftime("%Y-%m-%d"),
                    time_end.strftime("%Y-%m-%d"),
                ),
                count=max_results,
            )
        except Exception as exc:
            logger.error("earthaccess search failed: %s", exc)
            return []

        observations: list[dict[str, Any]] = []

        for granule in results:
            try:
                umm = granule.get("umm", granule)
                if isinstance(umm, dict):
                    spatial = umm.get("SpatialExtent", {})
                    temporal_info = umm.get("TemporalExtent", {})
                else:
                    spatial = {}
                    temporal_info = {}

                # Extract bounding box from granule metadata
                horiz = spatial.get("HorizontalSpatialDomain", {})
                geom = horiz.get("Geometry", {})
                bboxes = geom.get("BoundingRectangles", [])
                if bboxes:
                    bb = bboxes[0]
                    lon = (bb.get("WestBoundingCoordinate", 0) + bb.get("EastBoundingCoordinate", 0)) / 2
                    lat = (bb.get("SouthBoundingCoordinate", 0) + bb.get("NorthBoundingCoordinate", 0)) / 2
                else:
                    lon, lat = (w + e) / 2, (s + n) / 2

                # Extract temporal
                range_dts = temporal_info.get("RangeDateTime", {})
                begin = range_dts.get("BeginningDateTime", "")
                try:
                    ts = datetime.fromisoformat(str(begin).replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    ts = time_start

                # Extract data links
                related = umm.get("RelatedUrls", []) if isinstance(umm, dict) else []
                data_urls = [
                    u.get("URL", "")
                    for u in related
                    if u.get("Type") in ("GET DATA", "GET DATA VIA DIRECT ACCESS")
                ]

                granule_id = ""
                meta = granule.get("meta", {})
                if isinstance(meta, dict):
                    granule_id = meta.get("concept-id", meta.get("native-id", ""))

                observations.append({
                    "obs_type": "satellite",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"nasa-{granule_id}",
                    "source_name": f"NASA Earthdata ({short_name})",
                    "quality_score": 0.95,
                    "payload": {
                        "short_name": short_name,
                        "granule_id": granule_id,
                        "data_urls": data_urls[:3],
                        "size_mb": meta.get("granule-size") if isinstance(meta, dict) else None,
                        "collection": short_name,
                        "description": OCEAN_DATASETS.get(short_name, ""),
                    },
                })

            except Exception as exc:
                logger.debug("Skipping granule: %s", exc)
                continue

        return observations

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Search NASA Earthdata granules within bbox and time range.

        Extra params:
            short_name: NASA dataset short name (e.g. 'MUR-JPL-L4-GLOB-v4.1')
                       Default: MUR SST. Use list_datasets() for options.
        """
        short_name = params.get("short_name", "MUR-JPL-L4-GLOB-v4.1")
        limit = params.get("limit", 100)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self._search_sync, bbox, time_start, time_end, short_name, limit,
        )

        logger.info("earthaccess returned %d granules for %s", len(results), short_name)
        return results

    @staticmethod
    def list_datasets() -> dict[str, str]:
        """Return known ocean-relevant NASA datasets."""
        return dict(OCEAN_DATASETS)
