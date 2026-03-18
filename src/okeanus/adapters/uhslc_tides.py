"""UHSLC Tides adapter — global hourly tide gauge data.

The University of Hawaii Sea Level Center (UHSLC) operates ~300 tide gauge
stations worldwide and publishes data via ERDDAP. This adapter queries the
fast-delivery hourly sea level dataset. No auth required.

Source: https://uhslc.soest.hawaii.edu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ERDDAP_BASE = "https://uhslc.soest.hawaii.edu/erddap/tabledap"
DATASET_ID = "global_hourly_fast"


class UhslcTidesAdapter(BaseAdapter):
    """Connector for UHSLC global hourly tide gauge data (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "uhslc_tides"

    @property
    def source_url(self) -> str:
        return "https://uhslc.soest.hawaii.edu/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    @staticmethod
    def _lon_to_360(lon: float) -> float:
        """Convert longitude from -180..180 to 0..360 range used by UHSLC ERDDAP."""
        return lon % 360.0

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch hourly tide gauge data from UHSLC ERDDAP.

        Extra params:
            station_name: Filter by station name substring
            limit: Max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        station_name = params.get("station_name", "")

        ts_start = time_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        ts_end = time_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        variables = "station_name,station_country,uhslc_id,longitude,latitude,time,sea_level"

        # UHSLC ERDDAP uses 0-360 longitude range, not -180 to 180
        w360 = self._lon_to_360(w)
        e360 = self._lon_to_360(e)
        # When bbox crosses the 0/360 meridian (e.g. -10..0 => 350..0), bump east
        if e360 <= w360:
            e360 += 360.0

        constraints = (
            f"&time>={ts_start}&time<={ts_end}"
            f"&latitude>={s}&latitude<={n}"
            f"&longitude>={w360}&longitude<={e360}"
        )
        if station_name:
            constraints += f'&station_name=~".*{station_name}.*"'

        url = (
            f"{ERDDAP_BASE}/{DATASET_ID}.json"
            f"?{variables}{constraints}"
            f'&orderByLimit("{limit}")'
        )

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("UHSLC ERDDAP fetch failed: %s", exc)
            return []

        table = data.get("table", {})
        col_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        if not rows:
            logger.info("UHSLC returned 0 records")
            return []

        # Build column index map
        idx = {name: i for i, name in enumerate(col_names)}
        time_i = idx.get("time")
        lat_i = idx.get("latitude")
        lon_i = idx.get("longitude")

        if time_i is None or lat_i is None or lon_i is None:
            logger.warning("UHSLC missing required columns: %s", col_names)
            return []

        observations: list[dict[str, Any]] = []

        for row in rows:
            try:
                ts = datetime.fromisoformat(
                    str(row[time_i]).replace("Z", "+00:00")
                )
                lat = float(row[lat_i])
                lon = float(row[lon_i])
            except (ValueError, TypeError, IndexError):
                continue

            sea_level = row[idx["sea_level"]] if "sea_level" in idx else None

            observations.append({
                "obs_type": "sea_level",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"uhslc-{row[idx.get('uhslc_id', 0)] if 'uhslc_id' in idx else ''}-{ts.isoformat()}",
                "source_name": "UHSLC",
                "quality_score": 0.95,
                "payload": {
                    "station_name": row[idx["station_name"]] if "station_name" in idx else "",
                    "station_country": row[idx["station_country"]] if "station_country" in idx else "",
                    "uhslc_id": row[idx["uhslc_id"]] if "uhslc_id" in idx else "",
                    "sea_level_mm": sea_level,
                },
            })

        logger.info("UHSLC returned %d tide records", len(observations))
        return observations
