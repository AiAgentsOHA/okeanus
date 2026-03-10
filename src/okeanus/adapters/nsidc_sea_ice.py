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

BASE_URL = "https://noaadata.apps.nsidc.org/NOAA/G02135/seaice_analysis"


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

        csv_url = f"{BASE_URL}/{hemi_code}_Sea_Ice_Index_Regional_Monthly_Data_G02135_v3.0.csv"

        try:
            resp = await self._request("GET", csv_url)
            text = resp.text
        except Exception as exc:
            logger.error("NSIDC Sea Ice fetch failed: %s", exc)
            return []

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return []

        header = lines[0].split(",")
        observations: list[dict[str, Any]] = []

        for line in lines[1:]:
            cols = line.split(",")
            if len(cols) < len(header):
                continue

            row = dict(zip(header, cols))
            year_str = row.get("year", "").strip()
            month_str = row.get("month", row.get("mo", "")).strip()

            if not year_str or not month_str:
                continue

            try:
                year = int(year_str)
                month = int(month_str)
                ts = datetime(year, month, 1)
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            extent_str = row.get("extent", row.get("Extent", "")).strip()
            area_str = row.get("area", row.get("Area", "")).strip()

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

        logger.info("NSIDC Sea Ice returned %d records", len(observations))
        return observations
