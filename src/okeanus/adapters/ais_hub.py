"""AISHub adapter -- free community AIS vessel position data.

AISHub aggregates AIS data from community members who share their
receivers. Access requires a free API key (username).

API docs: https://www.aishub.net/api
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://data.aishub.net/ws.php"


class AisHubAdapter(BaseAdapter):
    """Connector for AISHub community AIS data (free API key required)."""

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._api_key = api_key or os.environ.get("AIS_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "aishub"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "real-time"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch AIS vessel positions within bbox from AISHub.

        Requires an API key (username) registered at aishub.net.
        Returns empty list if no key is configured.
        """
        if not self._api_key:
            logger.warning("AISHub adapter requires api_key (register at aishub.net)")
            return []

        w, s, e, n = bbox

        query_params: dict[str, Any] = {
            "username": self._api_key,
            "format": 1,  # JSON
            "output": "json",
            "compress": 0,
            "latmin": s,
            "latmax": n,
            "lonmin": w,
            "lonmax": e,
        }
        if mmsi := params.get("mmsi"):
            query_params["mmsi"] = mmsi

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("AISHub fetch failed: %s", exc)
            return []

        # AISHub returns errors as [{"ERROR": true, "ERROR_MESSAGE": "..."}]
        # Detect and log these before trying to parse vessel data.
        if isinstance(data, list) and len(data) >= 1 and isinstance(data[0], dict):
            if data[0].get("ERROR"):
                error_msg = data[0].get("ERROR_MESSAGE", "Unknown error")
                logger.error(
                    "AISHub API error: %s  "
                    "(AISHub requires an active data-sharing account; "
                    "see https://www.aishub.net/join)",
                    error_msg,
                )
                return []

        # AISHub returns a list with metadata at index 0 and records at index 1
        records: list[dict[str, Any]] = []
        if isinstance(data, list) and len(data) > 1:
            records = data[1] if isinstance(data[1], list) else []
        elif isinstance(data, list) and len(data) == 1:
            records = data[0] if isinstance(data[0], list) else []

        observations: list[dict[str, Any]] = []
        for rec in records:
            lat = rec.get("LATITUDE", rec.get("latitude"))
            lon = rec.get("LONGITUDE", rec.get("longitude"))
            if lat is None or lon is None:
                continue

            lat, lon = float(lat), float(lon)
            mmsi_val = rec.get("MMSI", rec.get("mmsi"))

            ts_str = rec.get("TIME", rec.get("time", ""))
            try:
                ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.now()

            # Filter by time window
            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"aishub-{mmsi_val}-{ts.isoformat()}",
                "source_name": "AISHub",
                "quality_score": 0.8,
                "payload": {
                    "mmsi": int(mmsi_val) if mmsi_val else None,
                    "vessel_name": rec.get("NAME", rec.get("name", "")),
                    "imo": rec.get("IMO", rec.get("imo")),
                    "callsign": rec.get("CALLSIGN", rec.get("callsign", "")),
                    "vessel_type": rec.get("TYPE", rec.get("type")),
                    "speed_knots": rec.get("SOG", rec.get("sog")),
                    "course_deg": rec.get("COG", rec.get("cog")),
                    "heading_deg": rec.get("HEADING", rec.get("heading")),
                    "destination": rec.get("DESTINATION", rec.get("destination", "")),
                    "draught_m": rec.get("DRAUGHT", rec.get("draught")),
                    "nav_status": rec.get("NAVSTAT", rec.get("navstat")),
                },
            })

        logger.info("AISHub returned %d vessel positions", len(observations))
        return observations
