"""NOAA ocean surface data adapter — SST from JPL MUR and NOAA products.

The original RTOFS dataset (ncepRtofsG2DNowDailyDiag) was removed from
CoastWatch ERDDAP.  This adapter now uses:

  - **jplMURSST41** — JPL Multi-scale Ultra-high Resolution SST (1 km daily,
    near-real-time, 2002-present).  Hosted on CoastWatch ERDDAP, no auth.

Data source: https://coastwatch.pfeg.noaa.gov/erddap/griddap/jplMURSST41
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
DATASET_ID = "jplMURSST41"


class NoaaRtofsAdapter(BaseAdapter):
    """Connector for global ocean SST via JPL MUR on ERDDAP (no auth).

    Returns daily sea-surface temperature at the bbox centroid.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_rtofs"

    @property
    def source_url(self) -> str:
        return f"{ERDDAP_BASE}/{DATASET_ID}"

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
        """Fetch ocean SST data at bbox centroid.

        Extra params:
            limit: max records (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)

        # Centroid query for time series
        lon = (w + e) / 2
        lat = (s + n) / 2

        # Limit time range to at most 30 days to keep response small
        max_range = timedelta(days=30)
        if (time_end - time_start) > max_range:
            time_start = time_end - max_range

        # MUR SST has ~2-day processing lag; clamp end date to avoid 404
        from datetime import timezone as _tz
        _now = datetime.now(_tz.utc)
        _lag = timedelta(days=3)
        if time_end > (_now - _lag):
            time_end = _now - _lag
        if time_start >= time_end:
            time_start = time_end - timedelta(days=7)

        ts_start = time_start.strftime("%Y-%m-%dT09:00:00Z")
        ts_end = time_end.strftime("%Y-%m-%dT09:00:00Z")

        # MUR SST variable is "analysed_sst"; stride by 1 day
        url = (
            f"{ERDDAP_BASE}/{DATASET_ID}.csv"
            f"?analysed_sst[({ts_start}):1:({ts_end})]"
            f"[({lat}):1:({lat})]"
            f"[({lon}):1:({lon})]"
        )

        try:
            resp = await self._request("GET", url)
            text = resp.text
        except Exception as exc:
            logger.error("NOAA ocean SST (MUR) fetch failed: %s", exc)
            return []

        lines = text.strip().split("\n")
        if len(lines) < 3:
            return []

        headers = [h.strip() for h in lines[0].split(",")]
        observations: list[dict[str, Any]] = []

        for line in lines[2:]:  # Skip column names + units
            if len(observations) >= limit:
                break

            parts = line.split(",")
            if len(parts) < len(headers):
                continue

            row = dict(zip(headers, parts))

            date_str = row.get("time", "")
            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            value = row.get("analysed_sst", "")
            try:
                val = float(value) if value else None
            except (ValueError, TypeError):
                val = None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"mursst-{lon:.2f}-{lat:.2f}-{ts.strftime('%Y%m%d')}",
                "source_name": "JPL MUR SST (NOAA ERDDAP)",
                "quality_score": 0.90,
                "payload": {
                    "variable": "sst",
                    "value": val,
                    "units": "degC",
                    "model": "JPL MUR SST v4.1",
                    "resolution": "1km",
                },
            })

        logger.info("NOAA ocean SST returned %d observations", len(observations))
        return observations
