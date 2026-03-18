"""Global Mangrove Watch (GMW) adapter.

Mangrove extent, loss, and gain data from the Global Mangrove Watch
initiative, a collaboration between JAXA, Aberystwyth University, and
soloEO. No auth required.

Data source: https://www.globalmangrovewatch.org/
API: https://github.com/globalmangrovewatch/gmw-api (Vizzuality Rails app)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# The GMW Heroku API provides location-based mangrove extent data
API_BASE = "https://mangrove-atlas-api.herokuapp.com/api/v2"


class GlobalMangroveAdapter(BaseAdapter):
    """Connector for Global Mangrove Watch (GMW) via Vizzuality API (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "global_mangrove"

    @property
    def source_url(self) -> str:
        return "https://www.globalmangrovewatch.org/"

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
        """Fetch mangrove extent data for locations within bbox.

        The GMW API is location-based (countries/regions), not spatial-query
        based.  We fetch all locations, filter by bbox intersection, then
        return metadata for each matching location.

        Extra params:
            limit: max locations to return (default 50)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 50)

        # Step 1: fetch all locations (lightweight, ~3000 entries)
        try:
            resp = await self._request("GET", f"{API_BASE}/locations")
            data = resp.json()
        except Exception as exc:
            logger.error("Global Mangrove Watch locations fetch failed: %s", exc)
            return []

        locations = data.get("data", [])
        if not isinstance(locations, list):
            logger.warning("GMW unexpected locations format: %s", type(locations))
            return []

        # Step 2: filter locations whose bounds intersect the query bbox
        matching: list[dict[str, Any]] = []
        for loc in locations:
            bounds = loc.get("bounds")
            if not bounds or not isinstance(bounds, dict):
                continue

            # Extract all coordinate points from Polygon or MultiPolygon
            btype = bounds.get("type", "")
            coords = bounds.get("coordinates", [])
            all_points: list[list[float]] = []
            if btype == "Polygon" and coords:
                # Polygon: coords = [ring, ...], ring = [[lon, lat], ...]
                for ring in coords:
                    if isinstance(ring, list):
                        for pt in ring:
                            if isinstance(pt, list) and len(pt) >= 2:
                                all_points.append(pt)
            elif btype == "MultiPolygon" and coords:
                # MultiPolygon: coords = [polygon, ...], polygon = [ring, ...]
                for polygon in coords:
                    if isinstance(polygon, list):
                        for ring in polygon:
                            if isinstance(ring, list):
                                for pt in ring:
                                    if isinstance(pt, list) and len(pt) >= 2:
                                        all_points.append(pt)

            if not all_points:
                continue

            lons = [pt[0] for pt in all_points]
            lats = [pt[1] for pt in all_points]
            loc_w, loc_e = min(lons), max(lons)
            loc_s, loc_n = min(lats), max(lats)
            # Check bbox intersection
            if loc_e < w or loc_w > e or loc_n < s or loc_s > n:
                continue
            matching.append(loc)
            if len(matching) >= limit:
                break

        if not matching:
            logger.info("GMW: no locations intersect bbox %s", bbox)
            return []

        # Step 3: get global habitat extent data (single call, returns yearly)
        try:
            resp2 = await self._request(
                "GET", f"{API_BASE}/widgets/habitat_extent"
            )
            extent_data = resp2.json()
        except Exception as exc:
            logger.warning("GMW extent widget failed: %s", exc)
            extent_data = {}

        global_extent: dict[int, float] = {}
        for entry in extent_data.get("data", []):
            yr = entry.get("year")
            if yr:
                global_extent[yr] = entry.get("value")

        # Step 4: build observations from matching locations
        observations: list[dict[str, Any]] = []
        years = sorted(global_extent.keys(), reverse=True)
        ts_year = years[0] if years else 2020
        try:
            ts = datetime(int(ts_year), 1, 1)
        except (ValueError, TypeError):
            ts = datetime(2020, 1, 1)

        for loc in matching:
            name = loc.get("name", "")
            iso = loc.get("iso", "")
            loc_id = loc.get("location_id", "")
            loc_type = loc.get("location_type", "")
            coast_m = loc.get("coast_length_m")
            area_m2 = loc.get("area_m2")

            # Extract centroid from bounds geometry
            bounds = loc.get("bounds", {})
            btype = bounds.get("type", "")
            coords = bounds.get("coordinates", [])
            all_pts: list[list[float]] = []
            if btype == "Polygon" and coords:
                for ring in coords:
                    if isinstance(ring, list):
                        for pt in ring:
                            if isinstance(pt, list) and len(pt) >= 2:
                                all_pts.append(pt)
            elif btype == "MultiPolygon" and coords:
                for polygon in coords:
                    if isinstance(polygon, list):
                        for ring in polygon:
                            if isinstance(ring, list):
                                for pt in ring:
                                    if isinstance(pt, list) and len(pt) >= 2:
                                        all_pts.append(pt)
            if not all_pts:
                continue
            center_lon = sum(pt[0] for pt in all_pts) / len(all_pts)
            center_lat = sum(pt[1] for pt in all_pts) / len(all_pts)

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [center_lon, center_lat],
                },
                "source_id": f"gmw-{loc_id or iso}",
                "source_name": "Global Mangrove Watch",
                "quality_score": 0.8,
                "payload": {
                    "location_name": name,
                    "iso": iso,
                    "location_type": loc_type,
                    "coast_length_m": coast_m,
                    "area_m2": area_m2,
                    "global_extent_ha": global_extent.get(ts_year),
                    "available_years": years[:5] if years else [],
                },
            })

        logger.info("Global Mangrove Watch returned %d locations", len(observations))
        return observations
