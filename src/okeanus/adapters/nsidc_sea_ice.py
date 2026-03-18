"""NSIDC Sea Ice Index adapter — Arctic and Antarctic sea ice extent.

Monthly and daily sea ice extent and area data from the National Snow
and Ice Data Center (NSIDC). No auth required.

Data source: https://nsidc.org/data/seaice_index
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://noaadata.apps.nsidc.org/NOAA/G02135"


class NsidcSeaIceAdapter(BaseAdapter):
    """Connector for NSIDC Sea Ice Index data (no auth required).

    Returns monthly sea ice extent/area values for the Arctic or Antarctic.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "nsidc_sea_ice"

    @property
    def source_url(self) -> str:
        return "https://nsidc.org/data/seaice_index"

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
        """Fetch sea ice extent data.

        Extra params:
            hemisphere: 'north' (default) or 'south'
        """
        hemisphere = params.get("hemisphere", "north")
        hemi_code = "N" if hemisphere == "north" else "S"
        hemi_dir = "north" if hemisphere == "north" else "south"

        # Fetch all 12 per-month CSV files and combine
        observations: list[dict[str, Any]] = []
        limit = params.get("limit", 500)

        for month_num in range(1, 13):
            csv_url = (
                f"{BASE_URL}/{hemi_dir}/monthly/data"
                f"/{hemi_code}_{month_num:02d}_extent_v4.0.csv"
            )
            try:
                resp = await self._request("GET", csv_url)
                text = resp.text
            except Exception:
                continue

            lines = text.strip().split("\n")
            if len(lines) < 2:
                continue

            header = [h.strip() for h in lines[0].split(",")]

            for line in lines[1:]:
                cols = line.split(",")
                if len(cols) < len(header):
                    continue

                row = dict(zip(header, cols))
                year_str = row.get("year", "").strip()
                month_str = row.get("mo", "").strip()

                if not year_str or not month_str:
                    continue

                try:
                    year = int(year_str)
                    month = int(month_str)
                    ts = datetime(year, month, 1, tzinfo=time_start.tzinfo)
                except (ValueError, TypeError):
                    continue

                if ts < time_start or ts > time_end:
                    continue

                extent_str = row.get("extent", "").strip()
                area_str = row.get("area", "").strip()

                try:
                    extent = float(extent_str) if extent_str and extent_str != "-9999" else None
                except ValueError:
                    extent = None
                try:
                    area = float(area_str) if area_str and area_str != "-9999" else None
                except ValueError:
                    area = None

                pole_lat = 90.0 if hemisphere == "north" else -90.0

                observations.append({
                    "obs_type": "physical",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [0.0, pole_lat]},
                    "source_id": f"nsidc-ice-{hemi_code}-{year}-{month:02d}",
                    "source_name": "NSIDC Sea Ice Index",
                    "quality_score": 0.95,
                    "payload": {
                        "hemisphere": hemisphere,
                        "year": year,
                        "month": month,
                        "extent_million_km2": extent,
                        "area_million_km2": area,
                    },
                })
                if len(observations) >= limit:
                    break
            if len(observations) >= limit:
                break

        logger.info("NSIDC Sea Ice returned %d records", len(observations))
        return observations
