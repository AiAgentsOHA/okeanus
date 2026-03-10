"""Ocean Networks Canada (ONC) adapter — deep-sea observatories.

160+ instrumented sites across NE Pacific, Arctic, NW Atlantic.
CTD sensors (temperature, salinity, pressure), ADCP currents,
hydrophones, oxygen sensors, and more.

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
    """Connector for Ocean Networks Canada Oceans 3.0 API."""

    def __init__(
        self, *, api_token: str = "", **kwargs: Any,
    ) -> None:
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
        self,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[dict[str, Any]]:
        """List ONC deployment locations, filtered by bbox."""
        if not self._api_token:
            logger.warning(
                "ONC adapter requires api_token"
                " (free at oceannetworks.ca)",
            )
            return []

        params: dict[str, Any] = {
            "method": "get",
            "token": self._api_token,
            "deviceCategoryCode": "HYDROPHONE",
        }

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/locations", params=params,
            )
            locations = resp.json()
            if not isinstance(locations, list):
                return []
        except Exception as exc:
            logger.error("ONC location list failed: %s", exc)
            return []

        if bbox:
            w, s, e, n = bbox
            locations = [
                loc for loc in locations
                if (s <= loc.get("lat", 0) <= n
                    and w <= loc.get("lon", 0) <= e)
            ]

        return locations

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch scalar sensor data from ONC stations.

        Defaults to CTD (temperature/salinity/pressure).
        Pass device_category='OXYSENSOR' etc. to override.
        """
        if not self._api_token:
            logger.warning("ONC adapter requires api_token")
            return []

        device_category = params.get("device_category", "CTD")
        location_code = params.get("location_code", "")
        limit = params.get("limit", 100)

        # If no specific location, find locations in bbox
        if not location_code:
            locations = await self._find_locations(
                bbox, device_category,
            )
            if not locations:
                return []
        else:
            locations = [
                {"locationCode": location_code, "lat": 0, "lon": 0},
            ]

        observations: list[dict[str, Any]] = []

        for loc in locations[:5]:  # limit stations
            loc_code = loc.get("locationCode", "")
            lat = loc.get("lat", 0.0)
            lon = loc.get("lon", 0.0)

            data_params: dict[str, Any] = {
                "method": "getByLocation",
                "token": self._api_token,
                "locationCode": loc_code,
                "deviceCategoryCode": device_category,
                "dateFrom": time_start.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z",
                ),
                "dateTo": time_end.strftime(
                    "%Y-%m-%dT%H:%M:%S.000Z",
                ),
                "rowLimit": limit,
            }

            try:
                resp = await self._request(
                    "GET",
                    f"{BASE_URL}/scalardata",
                    params=data_params,
                )
                data = resp.json()
            except Exception as exc:
                logger.warning(
                    "ONC data fetch for %s failed: %s",
                    loc_code, exc,
                )
                continue

            loc_name = loc.get(
                "locationName",
                loc.get("description", loc_code),
            )

            sensor_data = data.get("sensorData", [])
            for sensor in sensor_data:
                sensor_name = sensor.get("sensorName", "")
                unit = sensor.get("unitOfMeasure", "")
                values = sensor.get("data", {}).get("values", [])
                times = sensor.get("data", {}).get(
                    "sampleTimes", [],
                )

                for ts_str, val in zip(times, values):
                    try:
                        ts = datetime.fromisoformat(
                            ts_str.replace("Z", "+00:00"),
                        )
                    except (ValueError, AttributeError):
                        continue

                    observations.append({
                        "obs_type": "physical",
                        "timestamp": ts,
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat],
                        },
                        "source_id": (
                            f"onc-{loc_code}"
                            f"-{sensor_name}"
                            f"-{ts.isoformat()}"
                        ),
                        "source_name": "ONC",
                        "quality_score": None,
                        "payload": {
                            "location_code": loc_code,
                            "location_name": loc_name,
                            "sensor_name": sensor_name,
                            "value": val,
                            "unit": unit,
                            "device_category": device_category,
                        },
                    })

        logger.info(
            "ONC returned %d observations", len(observations),
        )
        return observations

    async def _find_locations(
        self,
        bbox: tuple[float, float, float, float],
        device_category: str,
    ) -> list[dict[str, Any]]:
        """Find ONC locations in bbox with the given device."""
        params: dict[str, Any] = {
            "method": "get",
            "token": self._api_token,
            "deviceCategoryCode": device_category,
        }

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/locations", params=params,
            )
            locations = resp.json()
            if not isinstance(locations, list):
                return []
        except Exception as exc:
            logger.error("ONC location search failed: %s", exc)
            return []

        w, s, e, n = bbox
        filtered = []
        for loc in locations:
            lat = loc.get("lat")
            lon = loc.get("lon")
            if lat is None or lon is None:
                continue
            if s <= lat <= n and w <= lon <= e:
                filtered.append(loc)
        return filtered
