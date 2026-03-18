"""ICOADS (International Comprehensive Ocean-Atmosphere Data Set) adapter.

ICOADS is the most complete and extensive collection of surface marine
observations -- 455M+ records from 1662-present including ship, buoy,
and platform observations of SST, SLP, wind, humidity, etc.

Data accessed via NOAA CoastWatch ERDDAP. No auth required.

Data source: https://icoads.noaa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# ICOADS monthly 1-degree enhanced summaries via ERDDAP (griddap).
# Only use -180..180 longitude mirrors to avoid coordinate conversion.
_GRIDDAP_URLS = [
    "https://coastwatch.pfeg.noaa.gov/erddap/griddap/esrlIcoads1ge_LonPM180",
    "https://upwell.pfeg.noaa.gov/erddap/griddap/esrlIcoads1ge_LonPM180",
]

# Metadata endpoint used to discover the actual time coverage
_INFO_URLS = [
    "https://coastwatch.pfeg.noaa.gov/erddap/info/esrlIcoads1ge_LonPM180/index.json",
]


class IcoadsAdapter(BaseAdapter):
    """Connector for ICOADS surface marine observations (no auth required).

    Returns surface marine observations including SST, sea level pressure,
    wind speed/direction, and humidity from ships and buoys.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=30.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "icoads"

    @property
    def source_url(self) -> str:
        return "https://icoads.noaa.gov/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def _get_time_coverage_end(self) -> datetime | None:
        """Query ERDDAP metadata to find actual end of available data."""
        import httpx

        for info_url in _INFO_URLS:
            try:
                async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                    resp = await client.get(info_url)
                    resp.raise_for_status()
                    data = resp.json()
                    for row in data.get("table", {}).get("rows", []):
                        if row[2] == "time_coverage_end":
                            return datetime.fromisoformat(
                                row[4].replace("Z", "+00:00")
                            )
            except Exception:
                continue
        return None

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ICOADS marine observations (monthly 1-degree gridded).

        Uses the CoastWatch ERDDAP griddap endpoint for ICOADS enhanced
        monthly summaries.  Returns one record per grid cell per month.

        Extra params:
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 200)

        # Clamp to small region to keep ERDDAP queries fast
        if (e - w) > 10 or (n - s) > 10:
            center_lon = (w + e) / 2
            center_lat = (s + n) / 2
            w = center_lon - 3
            e = center_lon + 3
            s = center_lat - 3
            n = center_lat + 3

        # ICOADS monthly data lags ~2 months.  Query the server for the
        # actual end of coverage and clamp time_end accordingly so we
        # don't trigger ERDDAP 404 "query produced no matching results".
        coverage_end = await self._get_time_coverage_end()
        effective_end = time_end
        if coverage_end is not None:
            # Make both offset-aware for comparison
            if effective_end.tzinfo is None:
                from datetime import timezone
                effective_end = effective_end.replace(tzinfo=timezone.utc)
            if coverage_end.tzinfo is None:
                from datetime import timezone
                coverage_end = coverage_end.replace(tzinfo=timezone.utc)
            if effective_end > coverage_end:
                logger.info(
                    "ICOADS: clamping end date from %s to coverage end %s",
                    effective_end.isoformat(),
                    coverage_end.isoformat(),
                )
                effective_end = coverage_end
        else:
            # Fallback: assume data lags 2 months
            from datetime import timezone
            now = datetime.now(timezone.utc)
            fallback_end = now - timedelta(days=60)
            if effective_end.tzinfo is None:
                effective_end = effective_end.replace(tzinfo=timezone.utc)
            if effective_end > fallback_end:
                effective_end = fallback_end

        # Ensure start < end
        eff_start = time_start
        if eff_start.tzinfo is None:
            from datetime import timezone
            eff_start = eff_start.replace(tzinfo=timezone.utc)
        if eff_start >= effective_end:
            # Push start back 6 months before effective_end
            eff_start = effective_end - timedelta(days=180)

        # Limit time range to at most 3 months to keep queries fast
        max_span = timedelta(days=90)
        if effective_end - eff_start > max_span:
            eff_start = effective_end - max_span
        ts_start = eff_start.strftime("%Y-%m-%dT00:00:00Z")
        ts_end = effective_end.strftime("%Y-%m-%dT00:00:00Z")

        # Fetch only SST to minimize ERDDAP response time
        variables = ["sst"]
        # keyed by (time, lat, lon) -> {var: value_str, ...}
        grid_data: dict[tuple[str, str, str], dict[str, str]] = {}

        for base_url in _GRIDDAP_URLS:
            lon_w_q, lon_e_q = w, e

            vars_ok = 0
            vars_failed = 0
            for var in variables:
                constraint = (
                    f"[({ts_start}):1:({ts_end})]"
                    f"[({s}):1:({n})]"
                    f"[({lon_w_q}):1:({lon_e_q})]"
                )
                url = f"{base_url}.csv?{var}{constraint}"
                try:
                    resp = await self._request("GET", url)
                    text = resp.text
                    vars_ok += 1
                except Exception as exc:
                    logger.debug("ICOADS %s var=%s failed: %s", base_url, var, exc)
                    vars_failed += 1
                    continue  # skip this variable, try the rest

                lines = text.strip().split("\n")
                if len(lines) < 3:
                    continue

                for line in lines[2:]:  # skip headers + units
                    parts = line.split(",")
                    if len(parts) < 4:
                        continue
                    # columns: time, latitude, longitude, <var>
                    key = (parts[0].strip(), parts[1].strip(), parts[2].strip())
                    if key not in grid_data:
                        grid_data[key] = {}
                    grid_data[key][var] = parts[3].strip()

            if vars_ok > 0:
                if vars_failed > 0:
                    logger.warning(
                        "ICOADS: %d/%d variables failed on %s, continuing with partial data",
                        vars_failed, len(variables), base_url,
                    )
                break  # got at least some data from this mirror

        if not grid_data:
            logger.error("ICOADS fetch failed: all ERDDAP mirrors unreachable")
            return []

        observations: list[dict[str, Any]] = []

        for (time_str, lat_str, lon_str), vals in grid_data.items():
            if len(observations) >= limit:
                break

            try:
                lat = float(lat_str)
                lon_raw = float(lon_str)
                lon = lon_raw if lon_raw <= 180 else lon_raw - 360
            except (ValueError, TypeError):
                continue

            try:
                ts = datetime.fromisoformat(time_str.replace("Z", "+00:00")) if time_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            def _float(v: str) -> float | None:
                try:
                    return float(v) if v and v.strip() != "NaN" else None
                except (ValueError, TypeError):
                    return None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"icoads-{lon:.1f}-{lat:.1f}-{ts.strftime('%Y%m')}",
                "source_name": "ICOADS",
                "quality_score": 0.85,
                "payload": {
                    "sst_c": _float(vals.get("sst", "")),
                },
            })

        logger.info("ICOADS returned %d observations", len(observations))
        return observations
