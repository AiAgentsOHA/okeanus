"""NDBC (National Data Buoy Center) adapter.

900+ weather stations — wind, pressure, air temp, SST, wave height/period.
Uses the NDBC SOS (Sensor Observation Service) JSON endpoint.

API: https://sdf.ndbc.noaa.gov/sos/server.shtml
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# NDBC stations are accessible via their ERDDAP or direct feeds
STATION_URL = "https://www.ndbc.noaa.gov/data/realtime2"
METADATA_URL = "https://www.ndbc.noaa.gov/activestations.xml"
# Use the NDBC ERDDAP for structured queries
ERDDAP_URL = "https://dods.ndbc.noaa.gov/thredds"


class NdbcAdapter(BaseAdapter):
    """Connector for NDBC buoy observations via direct station feeds."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        # Known stations with approximate locations for bbox filtering
        self._station_cache: list[dict[str, Any]] | None = None

    @property
    def source_name(self) -> str:
        return "ndbc"

    @property
    def source_url(self) -> str:
        return "https://www.ndbc.noaa.gov/"

    @property
    def update_frequency(self) -> str:
        return "hourly"

    async def _fetch_station_data(self, station_id: str) -> list[dict[str, Any]]:
        """Fetch latest observations from a specific buoy station."""
        url = f"{STATION_URL}/{station_id}.txt"
        try:
            resp = await self._request("GET", url)
            text = resp.text
        except Exception as exc:
            logger.warning("NDBC station %s fetch failed: %s", station_id, exc)
            return []

        lines = text.strip().split("\n")
        if len(lines) < 3:
            return []

        # First line is headers, second is units, data starts at line 3
        headers = lines[0].replace("#", "").split()
        records = []
        for line in lines[2:50]:  # limit to recent 48 records
            vals = line.split()
            if len(vals) >= len(headers):
                rec = dict(zip(headers, vals))
                records.append(rec)
        return records

    def _parse_record(
        self, rec: dict[str, Any], station_id: str, lat: float, lon: float,
    ) -> dict[str, Any] | None:
        """Convert a raw NDBC text record into an observation dict."""
        try:
            yr = int(rec.get("YY", 0))
            mo = int(rec.get("MM", 0))
            dd = int(rec.get("DD", 0))
            hh = int(rec.get("hh", 0))
            mm = int(rec.get("mm", 0))
            ts = datetime(yr, mo, dd, hh, mm, tzinfo=None)
        except (ValueError, TypeError):
            return None

        def safe_float(key: str) -> float | None:
            v = rec.get(key, "MM")
            if v == "MM" or v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        payload = {
            "station_id": station_id,
            "wind_dir_deg": safe_float("WDIR"),
            "wind_speed_ms": safe_float("WSPD"),
            "gust_speed_ms": safe_float("GST"),
            "wave_height_m": safe_float("WVHT"),
            "dom_wave_period_s": safe_float("DPD"),
            "avg_wave_period_s": safe_float("APD"),
            "pressure_hpa": safe_float("PRES"),
            "air_temp_c": safe_float("ATMP"),
            "water_temp_c": safe_float("WTMP"),
            "dewpoint_c": safe_float("DEWP"),
            "visibility_nm": safe_float("VIS"),
            "tide_m": safe_float("TIDE"),
        }

        return {
            "obs_type": "physical",
            "timestamp": ts,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "source_id": f"ndbc-{station_id}-{ts.isoformat()}",
            "source_name": "NDBC",
            "quality_score": 0.9,
            "payload": {k: v for k, v in payload.items() if v is not None},
        }

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch recent buoy data.

        Requires ``stations`` param as list of (station_id, lat, lon) tuples,
        since NDBC doesn't have a native bbox search API.
        """
        stations = params.get("stations", [])
        if not stations:
            logger.info("NDBC requires 'stations' param with [(id, lat, lon), ...]")
            return []

        observations: list[dict[str, Any]] = []
        for station_id, lat, lon in stations:
            w, s, e, n = bbox
            if not (s <= lat <= n and w <= lon <= e):
                continue

            records = await self._fetch_station_data(str(station_id))
            for rec in records:
                obs = self._parse_record(rec, str(station_id), lat, lon)
                if obs and time_start <= obs["timestamp"] <= time_end:
                    observations.append(obs)

        logger.info("NDBC returned %d observations", len(observations))
        return observations
