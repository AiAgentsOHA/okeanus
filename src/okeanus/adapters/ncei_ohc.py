"""NCEI Ocean Heat Content adapter — global ocean heat content anomalies.

NOAA's National Centers for Environmental Information publishes quarterly
ocean heat content analyses at 0-700m and 0-2000m depth layers. Data is
available as basin-averaged time series in ASCII format. No auth required.

File format: columns are YEAR, WO (World Ocean), WOse, NH, NHse, SH, SHse
for world ocean files; similar structure for individual basin files.

Source: https://www.ncei.noaa.gov/access/global-ocean-heat-content/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

OHC_BASE = "https://www.ncei.noaa.gov/data/oceans/woa/DATA_ANALYSIS/3M_HEAT_CONTENT/DATA/basin/3month"

# Basin codes used in file naming: h22-{code}-{depth}.dat
# w0=World Ocean, a0=Atlantic, i0=Indian, p0=Pacific
BASINS = {
    "world": {"code": "w0", "name": "World Ocean", "lat": 0.0, "lon": 0.0},
    "atlantic": {"code": "a0", "name": "Atlantic Ocean", "lat": 20.0, "lon": -40.0},
    "indian": {"code": "i0", "name": "Indian Ocean", "lat": -10.0, "lon": 70.0},
    "pacific": {"code": "p0", "name": "Pacific Ocean", "lat": 10.0, "lon": -160.0},
}


class NceiOhcAdapter(BaseAdapter):
    """Connector for NCEI global ocean heat content data (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ncei_ohc"

    @property
    def source_url(self) -> str:
        return "https://www.ncei.noaa.gov/access/global-ocean-heat-content/"

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
        """Fetch ocean heat content anomalies from NCEI.

        Extra params:
            depth_layer: '700m' or '2000m' (default '700m')
            basin: Basin key filter ('world', 'atlantic', 'indian', 'pacific')
            limit: Max records (default 200)
        """
        depth_layer = params.get("depth_layer", "700m")
        basin_filter = params.get("basin", "")
        limit = params.get("limit", 200)
        w, s, e, n = bbox

        observations: list[dict[str, Any]] = []

        for basin_key, basin_info in BASINS.items():
            if basin_filter and basin_key != basin_filter:
                continue

            # Check if basin representative point is in bbox
            blat, blon = basin_info["lat"], basin_info["lon"]
            if not (s <= blat <= n and w <= blon <= e):
                # For world, always include
                if basin_key != "world":
                    continue

            # Quarterly files: h22-{code}-{depth}{Q}.dat where Q=1-3,4-6,7-9,10-12
            code = basin_info["code"]
            quarters = ["1-3", "4-6", "7-9", "10-12"]

            for q_suffix in quarters:
                url = f"{OHC_BASE}/h22-{code}-{depth_layer}{q_suffix}.dat"

                try:
                    resp = await self._request("GET", url)
                    text = resp.text
                except Exception as exc:
                    logger.warning("NCEI OHC fetch %s Q%s failed: %s", basin_key, q_suffix, exc)
                    continue

                records = self._parse_ohc_ascii(
                    text, basin_key, basin_info, depth_layer,
                    time_start, time_end,
                )
                observations.extend(records)

            if len(observations) >= limit:
                observations = observations[:limit]
                break

        logger.info("NCEI OHC returned %d records", len(observations))
        return observations

    def _parse_ohc_ascii(
        self,
        text: str,
        basin_key: str,
        basin_info: dict[str, Any],
        depth_layer: str,
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Parse NCEI OHC ASCII data file.

        Format: YEAR  WO  WOse  NH  NHse  SH  SHse
        Year is decimal (e.g. 2005.125 = Q1 2005).
        """
        records: list[dict[str, Any]] = []
        header_cols: list[str] = []

        for line in text.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Detect header line
            if line.startswith("YEAR") or "WO" in line.split()[:3]:
                header_cols = line.split()
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            try:
                year_frac = float(parts[0])
                ohc_value = float(parts[1])  # First data column (WO or basin total)
            except (ValueError, IndexError):
                continue

            year = int(year_frac)
            frac = year_frac - year
            # Map fractional year to quarter midpoint month
            if frac < 0.25:
                month, quarter = 2, 1
            elif frac < 0.5:
                month, quarter = 5, 2
            elif frac < 0.75:
                month, quarter = 8, 3
            else:
                month, quarter = 11, 4

            try:
                ts = datetime(year, month, 15, tzinfo=timezone.utc)
            except (ValueError, OverflowError):
                continue

            if ts < time_start or ts > time_end:
                continue

            # Parse standard error if available
            ohc_se = None
            if len(parts) >= 3:
                try:
                    ohc_se = float(parts[2])
                except ValueError:
                    pass

            # Parse NH/SH values if available
            payload: dict[str, Any] = {
                "basin": basin_info["name"],
                "basin_key": basin_key,
                "depth_layer": depth_layer,
                "ohc_anomaly_10e22J": ohc_value,
                "ohc_anomaly_se": ohc_se,
                "year": year,
                "quarter": quarter,
            }

            # Add NH/SH breakdown if present
            if len(parts) >= 5:
                try:
                    payload["nh_anomaly"] = float(parts[3])
                    payload["nh_anomaly_se"] = float(parts[4])
                except (ValueError, IndexError):
                    pass
            if len(parts) >= 7:
                try:
                    payload["sh_anomaly"] = float(parts[5])
                    payload["sh_anomaly_se"] = float(parts[6])
                except (ValueError, IndexError):
                    pass

            records.append({
                "obs_type": "ocean_heat",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [basin_info["lon"], basin_info["lat"]],
                },
                "source_id": f"ncei-ohc-{basin_key}-{depth_layer}-{year}Q{quarter}",
                "source_name": "NCEI Ocean Heat Content",
                "quality_score": 0.95,
                "payload": payload,
            })

        return records
