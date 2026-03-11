"""NGDC Historical Tsunami Database adapter.

NOAA/NCEI Global Historical Tsunami Database contains records of
2,400+ events from 2100 BC to present. Queryable via NCEI hazards
REST API. No auth required.

Data source: https://www.ngdc.noaa.gov/hazard/tsu_db.shtml
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/tsunamis/events"


class NgdcTsunamiAdapter(BaseAdapter):
    """Connector for NGDC Historical Tsunami Database (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ngdc_tsunami"

    @property
    def source_url(self) -> str:
        return "https://www.ngdc.noaa.gov/hazard/tsu_db.shtml"

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
        """Fetch historical tsunami events within bbox.

        Extra params:
            min_magnitude: minimum tsunami magnitude
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "minLatitude": s,
            "maxLatitude": n,
            "minLongitude": w,
            "maxLongitude": e,
            "minYear": time_start.year,
            "maxYear": time_end.year,
        }

        min_mag = params.get("min_magnitude")
        if min_mag is not None:
            api_params["minEventMagnitude"] = min_mag

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("NGDC Tsunami fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("items", data.get("events", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("longitude")
            lat = rec.get("latitude")
            if lon is None or lat is None:
                continue

            try:
                lon, lat = float(lon), float(lat)
            except (ValueError, TypeError):
                continue

            year = rec.get("year")
            month = rec.get("month") or 1
            day = rec.get("day") or 1
            try:
                ts = datetime(int(year), int(month), int(day))
            except (ValueError, TypeError):
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"tsunami-{rec.get('id', '')}",
                "source_name": "NGDC Historical Tsunami",
                "quality_score": 0.9,
                "payload": {
                    "cause": rec.get("causeCode", rec.get("cause", "")),
                    "event_magnitude": rec.get("eventMagnitude"),
                    "max_water_height_m": rec.get("maxWaterHeight"),
                    "tsunami_intensity": rec.get("tsunamiIntensity"),
                    "deaths": rec.get("deaths"),
                    "injuries": rec.get("injuries"),
                    "damage_millions_usd": rec.get("damageMillionsDollars"),
                    "country": rec.get("country", ""),
                    "location": rec.get("locationName", ""),
                    "earthquake_magnitude": rec.get("eqMagnitude"),
                    "earthquake_depth_km": rec.get("eqDepth"),
                },
            })

        logger.info("NGDC Tsunami returned %d events", len(observations))
        return observations
