"""InterRidge Vents adapter — global hydrothermal vent database.

Locations and characteristics of known seafloor hydrothermal vents.
Maintained by the InterRidge community. No auth required.

Data source: https://vents-data.interridge.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://vents-data.interridge.org/api"


class InterRidgeAdapter(BaseAdapter):
    """Connector for InterRidge hydrothermal vent database (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "interridge"

    @property
    def source_url(self) -> str:
        return "https://vents-data.interridge.org/"

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
        """Fetch hydrothermal vent locations within bbox.

        Time range is largely ignored — vent locations are static reference data.

        Extra params:
            activity: 'active', 'inactive', 'inferred', or 'all' (default)
            max_depth_m: Maximum depth filter
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "minlon": w,
            "minlat": s,
            "maxlon": e,
            "maxlat": n,
            "limit": limit,
            "format": "json",
        }
        if activity := params.get("activity"):
            if activity != "all":
                api_params["activity"] = activity

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/ventfields", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("InterRidge fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("features", data.get("results", []))
        observations: list[dict[str, Any]] = []

        for rec in results:
            if not isinstance(rec, dict):
                continue

            # Handle GeoJSON-style or flat records
            if "geometry" in rec and "properties" in rec:
                coords = rec["geometry"].get("coordinates", [])
                props = rec["properties"]
                lon, lat = (coords[0], coords[1]) if len(coords) >= 2 else (None, None)
            else:
                lon = rec.get("longitude", rec.get("lon"))
                lat = rec.get("latitude", rec.get("lat"))
                props = rec

            if lon is None or lat is None:
                continue

            year = props.get("yearDiscovered") or props.get("year_discovered")
            try:
                ts = datetime(int(year), 1, 1) if year else datetime(2000, 1, 1)
            except (ValueError, TypeError):
                ts = datetime(2000, 1, 1)

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"interridge-{props.get('id', props.get('name_id', ''))}",
                "source_name": "InterRidge",
                "quality_score": 0.9,
                "payload": {
                    "vent_name": props.get("name", props.get("ventName", "")),
                    "activity": props.get("activity", ""),
                    "region": props.get("region", ""),
                    "ocean": props.get("ocean", ""),
                    "tectonic_setting": props.get("tectonicSetting", ""),
                    "max_depth_m": props.get("maxDepth", props.get("depth")),
                    "max_temp_c": props.get("maxTemp", props.get("temperature")),
                    "host_rock": props.get("hostRock", ""),
                    "minerals": props.get("minerals", ""),
                    "notes": str(props.get("notes", ""))[:500],
                },
            })

        logger.info("InterRidge returned %d vent fields", len(observations))
        return observations
