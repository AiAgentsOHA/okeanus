"""Ocean Networks Canada (ONC) adapter — hydrophone acoustic data.

160+ hydrophones across NE Pacific, Arctic, NW Atlantic.
Source of DeepShip + VTUAD labeled datasets.

API docs: https://data.oceannetworks.ca/OpenAPI
Note: Requires a free token from https://data.oceannetworks.ca/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://data.oceannetworks.ca/api"


class OncAdapter(BaseAdapter):
    """Connector for Ocean Networks Canada Oceans 3.0 API (free token required)."""

    def __init__(self, *, api_token: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._api_token = api_token

    @property
    def source_name(self) -> str:
        return "onc"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "real-time"

    async def list_locations(
        self, bbox: tuple[float, float, float, float] | None = None,
    ) -> list[dict[str, Any]]:
        """List ONC deployment locations, optionally filtered by bbox."""
        if not self._api_token:
            logger.warning("ONC adapter requires api_token (free at oceannetworks.ca)")
            return []

        params: dict[str, Any] = {
            "token": self._api_token,
            "deviceCategoryCode": "HYDROPHONE",
        }
        if bbox:
            w, s, e, n = bbox
            params.update({
                "locationCode": "",  # empty = all
                "minLat": s, "maxLat": n,
                "minLon": w, "maxLon": e,
            })

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/locations", params=params,
            )
            return resp.json() if isinstance(resp.json(), list) else []
        except Exception as exc:
            logger.error("ONC location list failed: %s", exc)
            return []

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch hydrophone data availability or scalar data from ONC stations."""
        if not self._api_token:
            logger.warning("ONC adapter requires api_token")
            return []

        location_code = params.get("location_code", "")
        device_category = params.get("device_category", "HYDROPHONE")

        # If no specific location, search for hydrophones in bbox
        if not location_code:
            locations = await self.list_locations(bbox)
            if not locations:
                return []
        else:
            locations = [{"locationCode": location_code}]

        observations: list[dict[str, Any]] = []

        for loc in locations[:10]:  # limit to 10 locations
            loc_code = loc.get("locationCode", "")
            lat = loc.get("latitude", loc.get("lat", 0.0))
            lon = loc.get("longitude", loc.get("lon", 0.0))

            # Fetch scalar data (SPL levels etc.) for this location
            data_params: dict[str, Any] = {
                "token": self._api_token,
                "locationCode": loc_code,
                "deviceCategoryCode": device_category,
                "dateFrom": time_start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "dateTo": time_end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "rowLimit": params.get("limit", 100),
            }

            try:
                resp = await self._request(
                    "GET", f"{BASE_URL}/scalardata", params=data_params,
                )
                data = resp.json()
            except Exception as exc:
                logger.warning("ONC data fetch for %s failed: %s", loc_code, exc)
                continue

            sensor_data = data.get("sensorData", [])
            for sensor in sensor_data:
                sensor_name = sensor.get("sensorName", "")
                values = sensor.get("data", {}).get("values", [])
                times = sensor.get("data", {}).get("sampleTimes", [])

                for ts_str, val in zip(times, values):
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        continue

                    observations.append({
                        "obs_type": "acoustic",
                        "timestamp": ts,
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "source_id": f"onc-{loc_code}-{sensor_name}-{ts.isoformat()}",
                        "source_name": "ONC Hydrophones",
                        "quality_score": None,
                        "payload": {
                            "location_code": loc_code,
                            "location_name": loc.get("description", loc.get("locationName", "")),
                            "sensor_name": sensor_name,
                            "value": val,
                            "unit": sensor.get("unitOfMeasure", ""),
                            "device_category": device_category,
                        },
                    })

        logger.info("ONC returned %d acoustic observations", len(observations))
        return observations
