"""HYCOM (HYbrid Coordinate Ocean Model) adapter -- global ocean forecast.

HYCOM provides global 1/12 degree ocean analysis/forecast data including
temperature, salinity, currents, and sea surface height.
Data served via NCEI ERDDAP griddap. No auth required.

Data source: https://www.hycom.org/
ERDDAP: https://www.ncei.noaa.gov/erddap/griddap/Hycom_sfc_3d
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# NCEI ERDDAP mirror of HYCOM GLBy0.08 global analysis (3D surface)
# Time coverage: 2013-03-05 to 2024-09-04 (may extend)
# Uses 0-360 longitude convention
ERDDAP_BASE = "https://www.ncei.noaa.gov/erddap/griddap"
DATASET_ID = "Hycom_sfc_3d"

# Time coverage end -- clamp queries to this date
TIME_COVERAGE_END = datetime(2024, 9, 4)


class HycomAdapter(BaseAdapter):
    """Connector for HYCOM global ocean model via NCEI ERDDAP (no auth).

    Returns ocean temperature, salinity, and current velocity
    from the GLBy0.08 1/12 degree global analysis.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "hycom"

    @property
    def source_url(self) -> str:
        return "https://www.hycom.org/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch HYCOM ocean model data within bbox via NCEI ERDDAP griddap.

        Extra params:
            variable: 'water_temp' (default), 'salinity', 'water_u', 'water_v'
            depth: depth in meters (default: 0 = surface)
            limit: max grid points (default 200)
        """
        w, s, e, n = bbox
        variable = params.get("variable", "water_temp")
        depth = params.get("depth", 0.0)
        limit = params.get("limit", 200)

        # Map variable names to ERDDAP variable names
        var_map = {
            "water_temp": "water_temp",
            "temperature": "water_temp",
            "salinity": "salinity",
            "water_u": "water_u",
            "water_v": "water_v",
            "current_u": "water_u",
            "current_v": "water_v",
        }
        var_name = var_map.get(variable, "water_temp")

        # Clamp bbox to avoid huge requests (max 10 deg span)
        if (e - w) > 10 or (n - s) > 10:
            center_lon = (w + e) / 2
            center_lat = (s + n) / 2
            w = center_lon - 5
            e = center_lon + 5
            s = center_lat - 5
            n = center_lat + 5

        # HYCOM ERDDAP uses 0-360 longitude
        lon_w = w % 360 if w < 0 else w
        lon_e = e % 360 if e < 0 else e
        # If the conversion creates a backwards range, swap
        if lon_w > lon_e:
            lon_w, lon_e = lon_e, lon_w

        # Clamp time to dataset coverage -- data ends ~2024-09-04
        eff_end = min(time_end.replace(tzinfo=None), TIME_COVERAGE_END)
        eff_start = min(time_start.replace(tzinfo=None), eff_end - timedelta(days=1))

        ts_str = eff_end.strftime("%Y-%m-%dT00:00:00Z")

        # Build ERDDAP griddap query.
        # Format: var[(time)][(depth)][(lat_start):(lat_end)][(lon_start):(lon_end)]
        # Use percent-encoded brackets for httpx compatibility
        query = (
            f"{var_name}"
            f"%5B({ts_str})%5D"
            f"%5B({depth})%5D"
            f"%5B({s}):({n})%5D"
            f"%5B({lon_w}):({lon_e})%5D"
        )
        url = f"{ERDDAP_BASE}/{DATASET_ID}.csv?{query}"

        try:
            resp = await self._request("GET", url)
            text = resp.text
        except Exception as exc:
            logger.error("HYCOM ERDDAP fetch failed: %s", exc)
            return []

        # Parse CSV response
        lines = text.strip().split("\n")
        if len(lines) < 3:
            # ERDDAP CSV has header + units row + data rows
            return []

        headers = [h.strip() for h in lines[0].split(",")]
        # Skip units row (line[1])
        observations: list[dict[str, Any]] = []

        for line in lines[2:]:
            if len(observations) >= limit:
                break
            parts = line.split(",")
            if len(parts) < len(headers):
                continue

            row = dict(zip(headers, [p.strip() for p in parts]))

            try:
                lat = float(row.get("latitude", "0"))
                lon_360 = float(row.get("longitude", "0"))
                # Convert back to -180/+180
                lon = lon_360 - 360 if lon_360 > 180 else lon_360
            except (ValueError, TypeError):
                continue

            date_str = row.get("time", "")
            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else eff_end
            except (ValueError, TypeError):
                ts = eff_end

            value = row.get(var_name, "")
            try:
                val = float(value) if value else None
            except (ValueError, TypeError):
                val = None

            if val is None:
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"hycom-{lon:.3f}-{lat:.3f}-{ts.strftime('%Y%m%d') if hasattr(ts, 'strftime') else ''}",
                "source_name": "HYCOM",
                "quality_score": 0.85,
                "payload": {
                    "variable": var_name,
                    "value": val,
                    "depth_m": depth,
                    "model": "GLBy0.08 (NCEI mirror)",
                },
            })

        logger.info("HYCOM returned %d observations", len(observations))
        return observations
