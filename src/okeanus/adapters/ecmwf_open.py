"""ECMWF Open Data adapter -- global weather and wave forecasts.

Free access to ECMWF IFS model forecasts via the Open-Meteo API which
serves ECMWF data as simple JSON. No auth required.

The original adapter required the ecmwf-opendata + cfgrib packages.
This version uses the Open-Meteo API (api.open-meteo.com) which
redistributes ECMWF IFS 0.25-degree data over a lightweight REST API.

Docs: https://open-meteo.com/en/docs/ecmwf-api
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Open-Meteo ECMWF forecast endpoint (serves ECMWF IFS 0.25deg data)
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

# Map friendly names to Open-Meteo variable codes
_WEATHER_VARS = {
    "wind": "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
    "pressure": "pressure_msl",
    "temperature": "temperature_2m",
    "precipitation": "precipitation",
}

_MARINE_VARS = {
    "wave": "wave_height,wave_period,wave_direction",
    "swell": "swell_wave_height,swell_wave_period,swell_wave_direction",
    "sst": "ocean_current_velocity,ocean_current_direction",
}


class EcmwfOpenAdapter(BaseAdapter):
    """Connector for ECMWF forecast data via Open-Meteo (no auth required).

    Returns hourly forecast grid points as observation dicts. Uses the
    Open-Meteo API which serves ECMWF IFS 0.25-degree deterministic
    forecasts as simple JSON.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=30.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ecmwf_open"

    @property
    def source_url(self) -> str:
        return "https://open-meteo.com/en/docs/ecmwf-api"

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
        """Fetch ECMWF forecast data within bbox via Open-Meteo.

        Extra params:
            variable: 'wind' (default), 'wave', 'pressure', 'temperature',
                      'sst', 'precipitation', 'swell'
            limit: Max observations to return (default 500)
        """
        variable = params.get("variable", "wind")
        limit = params.get("limit", 500)

        w, s, e, n = bbox

        # Generate a grid of points within the bbox (0.5-degree spacing)
        step = 0.5
        lats = []
        lons = []
        lat = s
        while lat <= n:
            lon = w
            while lon <= e:
                lats.append(round(lat, 2))
                lons.append(round(lon, 2))
                lon += step
            lat += step

        # Cap the number of grid points to avoid excessive requests
        max_points = min(len(lats), limit, 50)
        lats = lats[:max_points]
        lons = lons[:max_points]

        if not lats:
            return []

        # Determine if this is a marine or weather variable
        is_marine = variable in _MARINE_VARS

        if is_marine:
            url = MARINE_URL
            hourly_vars = _MARINE_VARS.get(variable, _MARINE_VARS["wave"])
        else:
            url = FORECAST_URL
            hourly_vars = _WEATHER_VARS.get(variable, _WEATHER_VARS["wind"])

        observations: list[dict[str, Any]] = []

        # Open-Meteo supports comma-separated lat/lon for multi-point queries
        # but only up to ~50 points. Process in batches.
        batch_size = 50
        for i in range(0, len(lats), batch_size):
            batch_lats = lats[i : i + batch_size]
            batch_lons = lons[i : i + batch_size]

            api_params: dict[str, Any] = {
                "latitude": ",".join(str(x) for x in batch_lats),
                "longitude": ",".join(str(x) for x in batch_lons),
                "hourly": hourly_vars,
                "forecast_days": 1,
            }

            if not is_marine:
                api_params["models"] = "ecmwf_ifs025"

            try:
                resp = await self._request("GET", url, params=api_params)
                data = resp.json()
            except Exception as exc:
                logger.error("ECMWF/Open-Meteo fetch failed: %s", exc)
                continue

            # Handle single-point vs multi-point response format
            if isinstance(data, list):
                point_results = data
            elif isinstance(data, dict) and "hourly" in data:
                point_results = [data]
            else:
                continue

            for point_data in point_results:
                if not isinstance(point_data, dict):
                    continue

                pt_lat = point_data.get("latitude", 0)
                pt_lon = point_data.get("longitude", 0)
                hourly = point_data.get("hourly", {})

                times = hourly.get("time", [])
                if not times:
                    continue

                # Get the first forecast timestep values
                for t_idx, time_str in enumerate(times[:6]):
                    if len(observations) >= limit:
                        break

                    try:
                        ts = datetime.fromisoformat(time_str).replace(
                            tzinfo=timezone.utc
                        )
                    except (ValueError, AttributeError):
                        ts = time_start

                    payload: dict[str, Any] = {
                        "variable": variable,
                        "forecast_model": "ECMWF IFS 0.25deg",
                        "forecast_type": "HRES",
                    }

                    # Extract all variable values for this timestep
                    for var_name in hourly_vars.split(","):
                        values = hourly.get(var_name, [])
                        if t_idx < len(values) and values[t_idx] is not None:
                            payload[var_name] = values[t_idx]

                    observations.append(
                        {
                            "obs_type": "physical",
                            "timestamp": ts,
                            "geometry": {
                                "type": "Point",
                                "coordinates": [pt_lon, pt_lat],
                            },
                            "source_id": f"ecmwf-{variable}-{pt_lat:.2f}-{pt_lon:.2f}-{t_idx}",
                            "source_name": "ECMWF Open Data (via Open-Meteo)",
                            "quality_score": 0.95,
                            "payload": payload,
                        }
                    )

            if len(observations) >= limit:
                break

        logger.info("ECMWF returned %d forecast points", len(observations))
        return observations[:limit]
