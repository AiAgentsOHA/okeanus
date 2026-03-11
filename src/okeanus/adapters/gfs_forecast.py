"""GFS weather forecast adapter via Open-Meteo marine API.

NOAA Global Forecast System (GFS) marine weather data accessed through
the Open-Meteo API, which provides a clean REST interface over GFS
model output. No auth required.

Data source: https://open-meteo.com/en/docs/marine-weather-api
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://marine-api.open-meteo.com/v1/marine"


class GfsForecastAdapter(BaseAdapter):
    """Connector for GFS marine forecasts via Open-Meteo (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "gfs_forecast"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "6-hourly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch marine weather forecasts for bbox centroid.

        Extra params:
            resolution: grid step in degrees (default 1.0)
        """
        w, s, e, n = bbox
        resolution = params.get("resolution", 1.0)

        observations: list[dict[str, Any]] = []

        # Sample grid points across bbox
        import math
        lon_steps = max(1, min(int((e - w) / resolution), 5))
        lat_steps = max(1, min(int((n - s) / resolution), 5))

        for i in range(lon_steps):
            for j in range(lat_steps):
                lon = w + (i + 0.5) * (e - w) / lon_steps
                lat = s + (j + 0.5) * (n - s) / lat_steps

                api_params: dict[str, Any] = {
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": (
                        "wave_height,wave_direction,wave_period,"
                        "wind_wave_height,wind_wave_direction,"
                        "swell_wave_height,swell_wave_direction,swell_wave_period,"
                        "ocean_current_velocity,ocean_current_direction"
                    ),
                    "start_date": time_start.strftime("%Y-%m-%d"),
                    "end_date": time_end.strftime("%Y-%m-%d"),
                }

                try:
                    resp = await self._request("GET", BASE_URL, params=api_params)
                    data = resp.json()
                except Exception as exc:
                    logger.warning("GFS forecast fetch failed at %.2f,%.2f: %s", lon, lat, exc)
                    continue

                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                wave_heights = hourly.get("wave_height", [])
                wave_dirs = hourly.get("wave_direction", [])
                wave_periods = hourly.get("wave_period", [])
                current_vel = hourly.get("ocean_current_velocity", [])
                current_dir = hourly.get("ocean_current_direction", [])

                for k, t in enumerate(times):
                    try:
                        ts = datetime.fromisoformat(t)
                    except (ValueError, TypeError):
                        continue

                    observations.append({
                        "obs_type": "physical",
                        "timestamp": ts,
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "source_id": f"gfs-{lon:.2f}-{lat:.2f}-{t}",
                        "source_name": "GFS Marine Forecast",
                        "quality_score": 0.8,
                        "payload": {
                            "wave_height_m": wave_heights[k] if k < len(wave_heights) else None,
                            "wave_direction_deg": wave_dirs[k] if k < len(wave_dirs) else None,
                            "wave_period_s": wave_periods[k] if k < len(wave_periods) else None,
                            "current_velocity_ms": current_vel[k] if k < len(current_vel) else None,
                            "current_direction_deg": current_dir[k] if k < len(current_dir) else None,
                            "model": "GFS",
                        },
                    })

        logger.info("GFS forecast returned %d observations", len(observations))
        return observations
