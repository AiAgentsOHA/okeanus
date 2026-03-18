"""NDBC (National Data Buoy Center) adapter.

900+ weather stations — wind, pressure, air temp, SST, wave height/period.
Auto-discovers stations within bbox from the NDBC station table.

API: https://www.ndbc.noaa.gov/
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

STATION_URL = "https://www.ndbc.noaa.gov/data/realtime2"
ACTIVE_STATIONS_URL = "https://www.ndbc.noaa.gov/activestations.xml"


class NdbcAdapter(BaseAdapter):
    """Connector for NDBC buoy observations with auto station discovery."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
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

    async def _discover_stations(
        self, bbox: tuple[float, float, float, float],
    ) -> list[dict[str, Any]]:
        """Fetch active station list and filter by bbox."""
        if self._station_cache is not None:
            w, s, e, n = bbox
            return [
                st for st in self._station_cache
                if s <= st["lat"] <= n and w <= st["lon"] <= e
            ]

        try:
            resp = await self._request("GET", ACTIVE_STATIONS_URL)
            root = ET.fromstring(resp.text)
        except Exception as exc:
            logger.error("NDBC station discovery failed: %s", exc)
            return []

        stations = []
        for station in root.iter("station"):
            sid = station.get("id", "")
            lat = station.get("lat")
            lon = station.get("lon")
            if not sid or lat is None or lon is None:
                continue
            try:
                stations.append({
                    "id": sid,
                    "lat": float(lat),
                    "lon": float(lon),
                    "name": station.get("name", ""),
                    "type": station.get("type", ""),
                })
            except (ValueError, TypeError):
                continue

        self._station_cache = stations
        logger.info("NDBC discovered %d active stations", len(stations))

        w, s, e, n = bbox
        return [
            st for st in stations
            if s <= st["lat"] <= n and w <= st["lon"] <= e
        ]

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

        headers = lines[0].replace("#", "").split()
        records = []
        for line in lines[2:50]:
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
            from datetime import timezone
            ts = datetime(yr, mo, dd, hh, mm, tzinfo=timezone.utc)
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
        """Fetch recent buoy data. Auto-discovers stations in bbox."""
        max_stations = params.get("limit", 20)

        # Auto-discover stations in bbox
        stations = await self._discover_stations(bbox)
        if not stations:
            logger.info("No NDBC stations found in bbox %s", bbox)
            return []

        stations = stations[:max_stations]
        logger.info("Fetching data from %d NDBC stations in bbox", len(stations))

        observations: list[dict[str, Any]] = []
        for st in stations:
            records = await self._fetch_station_data(st["id"])
            for rec in records:
                obs = self._parse_record(rec, st["id"], st["lat"], st["lon"])
                if obs and time_start <= obs["timestamp"] <= time_end:
                    observations.append(obs)

        logger.info("NDBC returned %d observations", len(observations))
        return observations
