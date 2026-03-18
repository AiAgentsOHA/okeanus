"""NOAA CO-OPS (Center for Operational Oceanographic Products and Services) adapter.

Tides, water levels, currents, temperature, salinity at US coastal stations.
API has a 31-day max range per request.

API docs: https://api.tidesandcurrents.noaa.gov/api/prod/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod"
METADATA_URL = "https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi"


class NoaaCoopsAdapter(BaseAdapter):
    """Connector for NOAA CO-OPS Tides & Currents API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_coops"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "6-minute"

    async def _get_stations_in_bbox(
        self, bbox: tuple[float, float, float, float],
    ) -> list[dict[str, Any]]:
        w, s, e, n = bbox
        try:
            resp = await self._request(
                "GET", f"{METADATA_URL}/stations.json", params={"type": "waterlevels"},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA CO-OPS station list failed: %s", exc)
            return []

        stations = data.get("stations", [])
        return [
            st for st in stations
            if (st.get("lat") is not None and st.get("lng") is not None
                and s <= st["lat"] <= n and w <= st["lng"] <= e)
        ]

    async def _get_data(
        self,
        station_id: str,
        product: str,
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        # API has 31-day max range — use most recent 30 days
        begin = max(time_start, time_end - timedelta(days=30))
        params: dict[str, Any] = {
            "begin_date": begin.strftime("%Y%m%d"),
            "end_date": time_end.strftime("%Y%m%d"),
            "station": station_id,
            "product": product,
            "datum": "MLLW",
            "units": "metric",
            "time_zone": "gmt",
            "format": "json",
            "application": "okeanus",
        }
        try:
            resp = await self._request("GET", f"{BASE_URL}/datagetter", params=params)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA CO-OPS data fetch failed for %s: %s", station_id, exc)
            return []

        return data.get("data", [])

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        product = params.get("product", "water_level")
        max_stations = min(params.get("max_stations", 3), 5)

        # Narrow global bbox to US East Coast to avoid overwhelming station list
        w, s, e, n = bbox
        if (e - w) > 100 or (n - s) > 100:
            bbox = (-82.0, 24.0, -66.0, 45.0)

        stations = await self._get_stations_in_bbox(bbox)
        if not stations:
            logger.info("No NOAA CO-OPS stations found in bbox")
            return []

        stations = stations[:max_stations]
        observations: list[dict[str, Any]] = []
        limit = params.get("limit", 500)

        for station in stations:
            station_id = str(station.get("id", ""))
            lat = station.get("lat", 0.0)
            lon = station.get("lng", 0.0)
            name = station.get("name", "")

            records = await self._get_data(station_id, product, time_start, time_end)

            for rec in records:
                ts_str = rec.get("t", "")
                value = rec.get("v")
                if not ts_str or value is None:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_str.replace(" ", "T") + "+00:00")
                    val = float(value)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "physical",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"coops-{station_id}-{ts_str}",
                    "source_name": "NOAA CO-OPS",
                    "quality_score": 1.0 if rec.get("q") == "v" else 0.8,
                    "payload": {
                        "station_id": station_id,
                        "station_name": name,
                        "product": product,
                        "value": val,
                        "unit": "m",
                        "quality_flag": rec.get("q", ""),
                    },
                })
                if len(observations) >= limit:
                    break
            if len(observations) >= limit:
                break

        logger.info("NOAA CO-OPS returned %d observations from %d stations",
                     len(observations), len(stations))
        return observations
