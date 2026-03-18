"""InterRidge Vents adapter — global hydrothermal vent database.

Static dataset of 721 vent fields from PANGAEA. No auth required.
Data source: https://doi.pangaea.de/10.1594/PANGAEA.917894
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Direct link to the actual CSV data file hosted on PANGAEA
CSV_URL = (
    "https://hs.pangaea.de/Maps/Vents/InterRidge_Beaulieu_2020"
    "/vent_fields_all_20200325cleansorted.csv"
)


class InterRidgeAdapter(BaseAdapter):
    """Connector for InterRidge hydrothermal vent database (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "interridge"

    @property
    def source_url(self) -> str:
        return "https://vents-data.interridge.org/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        try:
            resp = await self._request("GET", CSV_URL)
            text = resp.text
        except Exception as exc:
            logger.error("InterRidge PANGAEA fetch failed: %s", exc)
            return []

        reader = csv.DictReader(io.StringIO(text))
        observations: list[dict[str, Any]] = []

        for row in reader:
            try:
                lat = float(row.get("Latitude", ""))
                lon = float(row.get("Longitude", ""))
            except (ValueError, TypeError):
                continue

            if not (w <= lon <= e and s <= lat <= n):
                continue

            name = row.get("Name.ID", "")
            depth_str = row.get("Maximum.or.Single.Reported.Depth", "")
            try:
                depth = float(depth_str) if depth_str and depth_str != "NA" else None
            except ValueError:
                depth = None

            observations.append({
                "obs_type": "physical",
                "timestamp": datetime(2020, 1, 1),  # Static reference data
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"interridge-{name or len(observations)}",
                "source_name": "InterRidge",
                "quality_score": 0.9,
                "payload": {
                    "vent_name": name,
                    "activity": row.get("Activity", ""),
                    "region": row.get("Region", ""),
                    "tectonic_setting": row.get("Tectonic.setting", ""),
                    "max_depth_m": depth,
                    "ocean": row.get("Ocean", ""),
                    "max_temperature": row.get("Maximum.Temperature", ""),
                },
            })
            if len(observations) >= limit:
                break

        logger.info("InterRidge returned %d vent fields", len(observations))
        return observations
