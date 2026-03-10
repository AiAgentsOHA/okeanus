"""Marine Heatwave (MHW) detection adapter.

Detects marine heatwaves from SST time series using the Hobday et al. (2016)
definition. Can use NOAA OISST or any ERDDAP SST preset as input.

Requires:  pip install xarray
Optional:  pip install marineHeatWaves (original package)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


def _detect_mhw(sst_series: list[float], dates: list[datetime], baseline_years: int = 30) -> list[dict[str, Any]]:
    """Detect marine heatwaves using Hobday et al. (2016) definition.

    A MHW is a period of 5+ consecutive days where SST exceeds the 90th
    percentile of a climatological baseline.

    Simple implementation when marineHeatWaves package is not available.
    """
    if len(sst_series) < 30:
        return []

    import statistics

    mean_sst = statistics.mean(sst_series)
    p90 = sorted(sst_series)[int(len(sst_series) * 0.9)]

    events: list[dict[str, Any]] = []
    in_event = False
    event_start = 0

    for i, (sst, dt) in enumerate(zip(sst_series, dates)):
        if sst > p90:
            if not in_event:
                in_event = True
                event_start = i
        else:
            if in_event:
                duration = i - event_start
                if duration >= 5:  # Hobday minimum 5 days
                    event_sst = sst_series[event_start:i]
                    events.append({
                        "start_date": dates[event_start],
                        "end_date": dates[i - 1],
                        "duration_days": duration,
                        "max_intensity_c": max(event_sst) - mean_sst,
                        "mean_intensity_c": statistics.mean(event_sst) - mean_sst,
                        "cumulative_intensity": sum(s - mean_sst for s in event_sst),
                        "max_sst_c": max(event_sst),
                        "threshold_c": p90,
                        "climatology_c": mean_sst,
                    })
                in_event = False

    # Handle event at end of series
    if in_event:
        duration = len(sst_series) - event_start
        if duration >= 5:
            event_sst = sst_series[event_start:]
            events.append({
                "start_date": dates[event_start],
                "end_date": dates[-1],
                "duration_days": duration,
                "max_intensity_c": max(event_sst) - mean_sst,
                "mean_intensity_c": statistics.mean(event_sst) - mean_sst,
                "cumulative_intensity": sum(s - mean_sst for s in event_sst),
                "max_sst_c": max(event_sst),
                "threshold_c": p90,
                "climatology_c": mean_sst,
            })

    return events


class MarineHeatwaveAdapter(BaseAdapter):
    """Marine heatwave detection from SST data.

    Fetches SST time series from ERDDAP (OISST) and applies MHW detection
    algorithm to identify heatwave events.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "marine_heatwave"

    @property
    def source_url(self) -> str:
        return "https://coastwatch.pfeg.noaa.gov/erddap"

    @property
    def update_frequency(self) -> str:
        return "daily"

    def _detect_sync(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Synchronous MHW detection — runs in executor."""
        try:
            import xarray as xr
        except ImportError:
            logger.error("xarray not installed: pip install xarray")
            return []

        w, s, e, n = bbox
        # Use centroid for single-point time series
        lon = (w + e) / 2
        lat = (s + n) / 2

        # Fetch SST from OISST via ERDDAP
        ts_start = time_start.strftime("%Y-%m-%dT00:00:00Z")
        ts_end = time_end.strftime("%Y-%m-%dT00:00:00Z")

        url = (
            f"https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg_LonPM180.csv"
            f"?sst[({ts_start}):1:({ts_end})]"
            f"[({lat}):1:({lat})]"
            f"[({lon}):1:({lon})]"
        )

        try:
            import httpx
            resp = httpx.get(url, timeout=60.0)
            resp.raise_for_status()
            lines = resp.text.strip().split("\n")
        except Exception as exc:
            logger.error("SST fetch for MHW failed: %s", exc)
            return []

        # Parse CSV (skip header rows)
        dates: list[datetime] = []
        sst_values: list[float] = []

        for line in lines[2:]:  # Skip column names + units
            parts = line.split(",")
            if len(parts) < 4:
                continue
            try:
                dt = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
                sst = float(parts[3])
                dates.append(dt)
                sst_values.append(sst)
            except (ValueError, IndexError):
                continue

        if not sst_values:
            return []

        # Try marineHeatWaves package first, fall back to built-in
        events: list[dict[str, Any]] = []
        try:
            import marineHeatWaves as mhw
            import numpy as np

            t_ordinal = [d.toordinal() for d in dates]
            mhws, clim = mhw.detect(np.array(t_ordinal), np.array(sst_values))

            for i in range(len(mhws.get("time_start", []))):
                events.append({
                    "start_date": dates[0] + timedelta(days=int(mhws["time_start"][i] - t_ordinal[0])),
                    "end_date": dates[0] + timedelta(days=int(mhws["time_end"][i] - t_ordinal[0])),
                    "duration_days": int(mhws["duration"][i]),
                    "max_intensity_c": float(mhws["intensity_max"][i]),
                    "mean_intensity_c": float(mhws["intensity_mean"][i]),
                    "cumulative_intensity": float(mhws["intensity_cumulative"][i]),
                    "category": int(mhws.get("category", [0] * (i + 1))[i]),
                })
        except (ImportError, Exception):
            events = _detect_mhw(sst_values, dates)

        # Convert events to observation dicts
        observations: list[dict[str, Any]] = []
        for evt in events:
            start_date = evt["start_date"]
            if isinstance(start_date, datetime):
                ts = start_date
            else:
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"mhw-{lon:.2f}-{lat:.2f}-{ts.strftime('%Y%m%d')}",
                "source_name": "Marine Heatwave Detection",
                "quality_score": 0.85,
                "payload": {
                    "event_type": "marine_heatwave",
                    "duration_days": evt.get("duration_days"),
                    "max_intensity_c": evt.get("max_intensity_c"),
                    "mean_intensity_c": evt.get("mean_intensity_c"),
                    "cumulative_intensity": evt.get("cumulative_intensity"),
                    "max_sst_c": evt.get("max_sst_c"),
                    "threshold_c": evt.get("threshold_c"),
                    "climatology_c": evt.get("climatology_c"),
                    "category": evt.get("category"),
                    "location": f"{lat:.2f}N, {abs(lon):.2f}{'W' if lon < 0 else 'E'}",
                },
            })

        return observations

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Detect marine heatwave events at bbox centroid over time range.

        Uses NOAA OISST daily SST and applies Hobday et al. (2016) detection.
        Longer time ranges (months to years) give better results.
        """
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self._detect_sync, bbox, time_start, time_end,
        )

        logger.info("MHW detection found %d events", len(results))
        return results
