"""PSMSL (Permanent Service for Mean Sea Level) adapter.

2,300+ tide gauge stations with monthly mean sea level records since 1807.
Longest continuous global sea level dataset. No auth required.

Data portal: https://psmsl.org/data/obtaining/
API docs: https://psmsl.org/data/obtaining/psmsl.helpjsondata.php
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://psmsl.org/api"


class PsmslAdapter(BaseAdapter):
    """Connector for PSMSL tide gauge sea level data (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "psmsl"

    @property
    def source_url(self) -> str:
        return "https://psmsl.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch tide gauge stations and their mean sea level data.

        First retrieves station list, filters by bbox, then fetches
        monthly mean sea level for matching stations.

        Extra params:
            station_id: Specific PSMSL station ID
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)

        # Fetch station metadata
        try:
            resp = await self._request("GET", f"{BASE_URL}/stations")
            stations = resp.json()
        except Exception as exc:
            logger.error("PSMSL station fetch failed: %s", exc)
            return []

        if not isinstance(stations, list):
            stations = stations.get("stations", [])

        # Filter stations by bbox
        matching: list[dict[str, Any]] = []
        for st in stations:
            lat = st.get("lat")
            lon = st.get("lon")
            if lat is None or lon is None:
                continue
            if w <= float(lon) <= e and s <= float(lat) <= n:
                matching.append(st)
            if len(matching) >= limit:
                break

        observations: list[dict[str, Any]] = []

        for st in matching:
            station_id = st.get("id")
            lat = float(st["lat"])
            lon = float(st["lon"])

            # Fetch monthly RLR data for this station
            try:
                resp = await self._request(
                    "GET", f"{BASE_URL}/stations/{station_id}/rlr/monthly",
                )
                monthly_data = resp.json()
            except Exception:
                # Fall back to station metadata only
                monthly_data = []

            if not isinstance(monthly_data, list):
                monthly_data = monthly_data.get("data", [])

            # Filter by time range and get most recent record
            recent = None
            for rec in monthly_data:
                year = rec.get("year")
                month = rec.get("month", 1)
                if year is None:
                    continue
                try:
                    ts = datetime(int(year), int(month), 1)
                except (ValueError, TypeError):
                    continue
                if time_start <= ts <= time_end:
                    if recent is None or ts > recent["ts"]:
                        recent = {"ts": ts, "rec": rec}

            if recent:
                ts = recent["ts"]
                rec = recent["rec"]
                msl = rec.get("rlr", rec.get("value"))
            else:
                ts = datetime.now()
                msl = None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"psmsl-{station_id}",
                "source_name": "PSMSL",
                "quality_score": 0.95,
                "payload": {
                    "station_id": station_id,
                    "station_name": st.get("name", ""),
                    "country": st.get("country", ""),
                    "coastline_code": st.get("coastlineCode"),
                    "station_code": st.get("stationCode"),
                    "mean_sea_level_mm": msl,
                    "quality_flag": st.get("qualityFlag", ""),
                    "gloss_id": st.get("glossId"),
                    "start_year": st.get("dateStart"),
                    "end_year": st.get("dateEnd"),
                },
            })

        logger.info("PSMSL returned %d tide gauge stations", len(observations))
        return observations
