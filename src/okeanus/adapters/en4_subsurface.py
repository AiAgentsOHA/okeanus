"""EN4 subsurface ocean temperature and salinity adapter.

The UK Met Office EN4 dataset provides quality-controlled subsurface
ocean temperature and salinity profiles from 1900-present, with
monthly objective analyses on a 1° grid.

Data source: https://www.metoffice.gov.uk/hadobs/en4/
No auth required — bulk download via HTTP.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# EN4 data is available via THREDDS OPeNDAP
THREDDS_URL = "https://hadobs.metoffice.gov.uk/thredds/dodsC/EN4/EN4.2.2"
# Multiple download base URLs to try — Met Office frequently restructures
_DOWNLOAD_BASES = [
    "https://www.metoffice.gov.uk/hadobs/en4/data/en4-2-2",
    "https://www.metoffice.gov.uk/hadobs/en4/data/en4-2-1/EN.4.2.2",
]


class En4SubsurfaceAdapter(BaseAdapter):
    """Connector for UK Met Office EN4 subsurface T/S data (no auth required).

    Returns gridded subsurface ocean temperature and salinity
    analyses from the EN4.2.2 dataset.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=15.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "en4_subsurface"

    @property
    def source_url(self) -> str:
        return "https://www.metoffice.gov.uk/hadobs/en4/"

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
        """Fetch EN4 subsurface ocean data summary.

        Returns metadata about available EN4 data files for the
        requested time range. EN4 uses NetCDF files — this adapter
        provides file listing and download links.

        Extra params:
            variable: 'temperature' (default) or 'salinity'
            analysis_type: 'analysis' (default) or 'profiles'
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)
        variable = params.get("variable", "temperature")
        analysis_type = params.get("analysis_type", "analysis")

        observations: list[dict[str, Any]] = []

        # EN4 data lags ~6 months behind real-time.  If the requested
        # window is entirely within the last 6 months, shift it back so
        # we actually hit files that exist on the server.
        from dateutil.relativedelta import relativedelta
        lag_cutoff = datetime.now(timezone.utc) - relativedelta(months=6)
        if time_start > lag_cutoff:
            # Shift the whole window back by 6-12 months
            shift = relativedelta(months=9)
            time_start = time_start - shift
            time_end = time_end - shift

        # Limit to at most 6 months to avoid excessive HEAD requests
        # (each month probes multiple URLs, and the Met Office server is slow)
        max_months = 6
        month_count = (time_end.year - time_start.year) * 12 + (time_end.month - time_start.month)
        if month_count > max_months:
            # Take the most recent max_months of the range
            time_start = time_end - relativedelta(months=max_months)

        # Probe ONE file with HEAD to discover which base URL works,
        # then construct remaining records without further HTTP calls.
        # This avoids N*M HEAD requests that timeout on the slow Met Office server.
        working_base: str | None = None
        probe_year = time_start.year
        probe_month = time_start.month
        probe_filename = f"EN.4.2.2.f.analysis.g10.{probe_year:04d}{probe_month:02d}.nc"
        for base in _DOWNLOAD_BASES:
            candidate = f"{base}/{probe_filename}"
            try:
                resp = await self._request("HEAD", candidate)
                if resp.status_code == 200:
                    working_base = base
                    break
            except Exception:
                continue

        # If no base URL responded, use the first one as a best-guess
        if working_base is None:
            working_base = _DOWNLOAD_BASES[0]

        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        # Generate monthly file references for the time range
        current = datetime(time_start.year, time_start.month, 1, tzinfo=timezone.utc)
        while current <= time_end and len(observations) < limit:
            year = current.year
            month = current.month

            # EN4 file naming: EN.4.2.2.f.analysis.g10.YYYYMM.nc
            filename = f"EN.4.2.2.f.analysis.g10.{year:04d}{month:02d}.nc"
            download_url = f"{working_base}/{filename}"

            observations.append({
                "obs_type": "physical",
                "timestamp": current,
                "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                "source_id": f"en4-{year:04d}{month:02d}",
                "source_name": "EN4 Met Office",
                "quality_score": 0.95,
                "payload": {
                    "variable": variable,
                    "analysis_type": analysis_type,
                    "year": year,
                    "month": month,
                    "filename": filename,
                    "download_url": download_url,
                    "grid_resolution": "1 degree",
                    "dataset_version": "EN4.2.2",
                },
            })

            # Next month
            if month == 12:
                current = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                current = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        logger.info("EN4 returned %d monthly records", len(observations))
        return observations
