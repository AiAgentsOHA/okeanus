"""Open-Meteo Marine adapter — free wave/wind/ocean forecast, no auth required.

Open-Meteo provides hourly marine weather forecasts including wave height,
wave period, wind speed, SST, and ocean current data. No API key needed.

API docs: https://open-meteo.com/en/docs/marine-weather-api
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://marine-api.open-meteo.com/v1/marine"


class OpenMeteoMarineAdapter(BaseAdapter):
    """Connector for Open-Meteo Marine weather forecast API (free, no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "open_meteo_marine"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "hourly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch marine forecast for points within bbox.

        The Open-Meteo marine API takes a single lat/lon point. For bbox
        queries we sample the center point. Pass latitude/longitude in
        params to override.

        Extra params:
            latitude: Specific latitude (default: bbox center)
            longitude: Specific longitude (default: bbox center)
            limit: Max hourly records (default 48)
        """
        w, s, e, n = bbox
        lat = params.get("latitude", (s + n) / 2)
        lon = params.get("longitude", (w + e) / 2)
        limit = params.get("limit", 48)

        hourly_vars = [
            "wave_height",
            "wave_direction",
            "wave_period",
            "wind_wave_height",
            "wind_wave_direction",
            "wind_wave_period",
            "swell_wave_height",
            "swell_wave_direction",
            "swell_wave_period",
            "ocean_current_velocity",
            "ocean_current_direction",
        ]

        query_params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join(hourly_vars),
            "timezone": "UTC",
        }

        # Add date range if within forecast window
        start_str = time_start.strftime("%Y-%m-%d")
        end_str = time_end.strftime("%Y-%m-%d")
        query_params["start_date"] = start_str
        query_params["end_date"] = end_str

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Open-Meteo Marine fetch failed: %s", exc)
            return []

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            return []

        observations: list[dict[str, Any]] = []
        resp_lat = data.get("latitude", lat)
        resp_lon = data.get("longitude", lon)

        for i, time_str in enumerate(times):
            if len(observations) >= limit:
                break

            try:
                ts = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            if ts < time_start or ts > time_end:
                continue

            payload: dict[str, Any] = {}
            for var in hourly_vars:
                values = hourly.get(var, [])
                if i < len(values) and values[i] is not None:
                    payload[var] = values[i]

            if not payload:
                continue

            observations.append({
                "obs_type": "marine_forecast",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [resp_lon, resp_lat],
                },
                "source_id": f"open-meteo-marine-{resp_lat}-{resp_lon}-{time_str}",
                "source_name": "Open-Meteo Marine",
                "quality_score": 0.8,
                "payload": payload,
            })

        logger.info("Open-Meteo Marine returned %d forecast hours", len(observations))
        return observations
