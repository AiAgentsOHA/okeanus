"""NOAA HABSOS adapter — Harmful Algal BloomS Observing System.

HAB cell counts and species observations along US coastal waters.
No auth required.

Data portal: https://habsos.noaa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://habsos.noaa.gov"


class HabsosAdapter(BaseAdapter):
    """Connector for NOAA HABSOS HAB cell count observations."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "habsos"

    @property
    def source_url(self) -> str:
        return BASE_URL

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
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "minLon": w,
            "minLat": s,
            "maxLon": e,
            "maxLat": n,
            "startDate": time_start.strftime("%m/%d/%Y"),
            "endDate": time_end.strftime("%m/%d/%Y"),
            "top": limit,
        }
        if species := params.get("species"):
            api_params["species"] = species
        if state := params.get("state"):
            api_params["state"] = state

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/api/observations", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("HABSOS fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("value", data.get("results", []))
        observations: list[dict[str, Any]] = []

        for rec in results:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("LONGITUDE", rec.get("longitude"))
            lat = rec.get("LATITUDE", rec.get("latitude"))
            if lon is None or lat is None:
                continue

            date_str = rec.get("SAMPLE_DATE") or rec.get("sampleDate", "")
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                else:
                    ts = datetime.fromisoformat(str(date_str) + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            cell_count = rec.get("CELLCOUNT", rec.get("cellCount"))

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"habsos-{rec.get('ID', rec.get('id', ''))}",
                "source_name": "HABSOS",
                "quality_score": 0.9,
                "payload": {
                    "species": rec.get("GENUS", rec.get("genus", ""))
                    + " " + rec.get("SPECIES", rec.get("species", "")),
                    "cell_count_per_l": cell_count,
                    "category": rec.get("CATEGORY", rec.get("category", "")),
                    "state": rec.get("STATE_ID", rec.get("state", "")),
                    "description": rec.get("DESCRIPTION", ""),
                    "sample_depth_m": rec.get("SAMPLE_DEPTH"),
                    "water_temp_c": rec.get("WATER_TEMP"),
                    "salinity_psu": rec.get("SALINITY"),
                },
            })

        logger.info("HABSOS returned %d observations", len(observations))
        return observations
