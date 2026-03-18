"""World Port Index adapter -- global port infrastructure from NGA.

The World Port Index (Pub 150) is published by the U.S. National
Geospatial-Intelligence Agency and contains data on approximately
3,700 ports worldwide. No authentication required.

Source: https://msi.nga.mil/Publications/WPI
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

WPI_CSV_URL = (
    "https://msi.nga.mil/api/publications/download"
    "?type=view&key=16920959/SFH00000/UpdatedPub150.csv"
)


class WorldPortIndexAdapter(BaseAdapter):
    """Connector for the NGA World Port Index (no auth required).

    Downloads the Pub 150 CSV and filters ports within the requested
    bounding box.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)
        self._cached_ports: list[dict[str, Any]] | None = None

    @property
    def source_name(self) -> str:
        return "world_port_index"

    @property
    def source_url(self) -> str:
        return "https://msi.nga.mil/Publications/WPI"

    @property
    def update_frequency(self) -> str:
        return "quarterly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ports within the bounding box from the World Port Index.

        Downloads and caches the full CSV, then filters by bbox.
        """
        if self._cached_ports is None:
            self._cached_ports = await self._download_ports()

        if not self._cached_ports:
            return []

        w, s, e, n = bbox
        observations: list[dict[str, Any]] = []

        for port in self._cached_ports:
            lat = port.get("lat")
            lon = port.get("lon")
            if lat is None or lon is None:
                continue
            if not (s <= lat <= n and w <= lon <= e):
                continue

            observations.append({
                "obs_type": "infrastructure",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"wpi-{port.get('index_no', '')}",
                "source_name": "World Port Index",
                "quality_score": 0.95,
                "payload": {
                    "port_name": port.get("port_name", ""),
                    "country": port.get("country", ""),
                    "un_locode": port.get("locode", ""),
                    "index_number": port.get("index_no", ""),
                    "harbor_size": port.get("harbor_size", ""),
                    "harbor_type": port.get("harbor_type", ""),
                    "shelter_afforded": port.get("shelter", ""),
                    "max_vessel_length": port.get("max_vessel_length", ""),
                    "max_vessel_draft": port.get("max_vessel_draft", ""),
                    "tide_range": port.get("tide_range", ""),
                },
            })

        logger.info("World Port Index returned %d ports", len(observations))
        return observations

    async def _download_ports(self) -> list[dict[str, Any]]:
        """Download and parse the World Port Index CSV."""
        try:
            resp = await self._request("GET", WPI_CSV_URL)
            text = resp.text
        except Exception as exc:
            logger.error("World Port Index download failed: %s", exc)
            return []

        ports: list[dict[str, Any]] = []
        try:
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                lat = self._parse_coord(
                    row.get("Latitude", row.get("latitude", ""))
                )
                lon = self._parse_coord(
                    row.get("Longitude", row.get("longitude", ""))
                )
                if lat is None or lon is None:
                    continue

                ports.append({
                    "lat": lat,
                    "lon": lon,
                    "port_name": (
                        row.get("Main Port Name", row.get("port_name", ""))
                    ),
                    "country": row.get("Country Code", row.get("country", "")),
                    "locode": row.get("UN/LOCODE", row.get("locode", "")),
                    "index_no": (
                        row.get("World Port Index Number", row.get("index_no", ""))
                    ),
                    "harbor_size": row.get("Harbor Size", row.get("harbor_size", "")),
                    "harbor_type": row.get("Harbor Type", row.get("harbor_type", "")),
                    "shelter": (
                        row.get("Shelter Afforded", row.get("shelter", ""))
                    ),
                    "max_vessel_length": row.get("Maximum Vessel Length", ""),
                    "max_vessel_draft": row.get("Maximum Vessel Draft", ""),
                    "tide_range": row.get("Tide Range", row.get("tide_range", "")),
                })
        except Exception as exc:
            logger.error("Failed to parse World Port Index CSV: %s", exc)
            return []

        logger.info("Cached %d ports from World Port Index", len(ports))
        return ports

    @staticmethod
    def _parse_coord(value: str) -> float | None:
        """Parse a coordinate value, handling various formats."""
        if not value:
            return None
        value = value.strip()
        try:
            return float(value)
        except ValueError:
            pass
        # Handle DMS-like strings (e.g., "40-42N" or "74-00W")
        try:
            value = value.upper()
            sign = 1
            if value.endswith(("S", "W")):
                sign = -1
                value = value[:-1]
            elif value.endswith(("N", "E")):
                value = value[:-1]
            parts = value.replace(":", "-").split("-")
            deg = float(parts[0])
            minutes = float(parts[1]) if len(parts) > 1 else 0
            seconds = float(parts[2]) if len(parts) > 2 else 0
            return sign * (deg + minutes / 60 + seconds / 3600)
        except (ValueError, IndexError):
            return None
