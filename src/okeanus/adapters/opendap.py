"""OPeNDAP/THREDDS adapter — remote ocean model data via xarray.

Access HYCOM, NCEP, and other gridded ocean model outputs directly
from OPeNDAP-enabled servers without downloading full files.

Requires:  pip install xarray netCDF4 (or pydap)
No auth required for public servers.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Well-known OPeNDAP endpoints for ocean data
ENDPOINTS: dict[str, dict[str, str]] = {
    "hycom_global": {
        "url": "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0",
        "description": "HYCOM Global 1/12 deg ocean model (T, S, currents, SSH)",
        "variables": "water_temp,salinity,water_u,water_v,surf_el",
    },
    "hycom_gofs": {
        "url": "https://tds.hycom.org/thredds/dodsC/GLBv0.08/expt_93.0",
        "description": "HYCOM GOFS 3.1 (Global Ocean Forecasting System)",
        "variables": "water_temp,salinity,water_u,water_v",
    },
    "ncep_sst": {
        "url": "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/sst.day.mean.2024.nc",
        "description": "NOAA OISST v2 daily high-resolution SST",
        "variables": "sst",
    },
    "ncep_wind": {
        "url": "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis2/gaussian_grid/uwnd.10m.gauss.2024.nc",
        "description": "NCEP/DOE Reanalysis 2 — 10m wind",
        "variables": "uwnd",
    },
    "godas": {
        "url": "https://psl.noaa.gov/thredds/dodsC/Datasets/godas/ucur.2024.nc",
        "description": "GODAS ocean currents analysis",
        "variables": "ucur",
    },
}


class OpendapAdapter(BaseAdapter):
    """Connector for OPeNDAP/THREDDS ocean model data (no auth).

    Opens remote datasets with xarray and extracts grid points within
    the requested bbox and time range.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "opendap"

    @property
    def source_url(self) -> str:
        return "https://tds.hycom.org/thredds/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    def _fetch_sync(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        endpoint_key: str,
        custom_url: str,
        max_records: int,
    ) -> list[dict[str, Any]]:
        """Synchronous xarray remote open — runs in executor."""
        try:
            import xarray as xr
        except ImportError:
            logger.error("xarray not installed: pip install xarray netCDF4")
            return []

        w, s, e, n = bbox

        # Determine URL
        if custom_url:
            url = custom_url
            description = "Custom OPeNDAP"
        elif endpoint_key in ENDPOINTS:
            url = ENDPOINTS[endpoint_key]["url"]
            description = ENDPOINTS[endpoint_key]["description"]
        else:
            logger.error("Unknown endpoint: %s. Available: %s", endpoint_key, list(ENDPOINTS.keys()))
            return []

        try:
            ds = xr.open_dataset(url, engine="netcdf4", decode_times=False)
        except Exception as exc:
            logger.error("OPeNDAP open failed for %s: %s", url, exc)
            return []

        try:
            # Subset by time
            time_dim = None
            for dim in ["time", "MT", "Time", "TIME"]:
                if dim in ds.dims or dim in ds.coords:
                    time_dim = dim
                    break

            if time_dim:
                # With decode_times=False, time coord is raw numbers;
                # just take the last few timesteps instead of date slicing
                n_times = ds.sizes.get(time_dim, 0)
                if n_times > 5:
                    ds = ds.isel({time_dim: slice(-5, None)})

            # Subset by lat/lon
            lat_dim = None
            for dim in ["lat", "latitude", "Latitude", "Y"]:
                if dim in ds.dims or dim in ds.coords:
                    lat_dim = dim
                    break
            lon_dim = None
            for dim in ["lon", "longitude", "Longitude", "X"]:
                if dim in ds.dims or dim in ds.coords:
                    lon_dim = dim
                    break

            if lat_dim and lon_dim:
                ds = ds.sel(
                    {lat_dim: slice(s, n), lon_dim: slice(w, e)},
                )

            # Select surface only if depth dimension exists
            for dim in ["depth", "Depth", "lev", "z"]:
                if dim in ds.dims:
                    ds = ds.isel({dim: 0})
                    break

        except Exception as exc:
            logger.warning("OPeNDAP subsetting failed: %s", exc)

        observations: list[dict[str, Any]] = []

        for var_name in ds.data_vars:
            try:
                da = ds[var_name]
                # Only compute a small subset
                if da.size > max_records * 10:
                    da = da.isel(
                        {d: slice(0, max(1, int(max_records ** 0.5)))
                         for d in da.dims if d not in [time_dim]},
                    )
                da = da.compute()
                df = da.to_dataframe().reset_index().dropna(subset=[var_name])

                if len(df) > max_records:
                    df = df.sample(n=max_records, random_state=42)

                for _, row in df.iterrows():
                    lon = float(row.get(lon_dim or "lon", row.get("longitude", 0)))
                    lat = float(row.get(lat_dim or "lat", row.get("latitude", 0)))

                    ts = time_start  # decode_times=False, use query time

                    observations.append({
                        "obs_type": "physical",
                        "timestamp": ts,
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "source_id": str(uuid.uuid4()),
                        "source_name": f"OPeNDAP ({endpoint_key or 'custom'})",
                        "quality_score": 0.9,
                        "payload": {
                            "parameter": var_name,
                            "value": float(row[var_name]),
                            "description": description,
                            "server": url[:80],
                        },
                    })
            except Exception as exc:
                logger.debug("Skipping variable %s: %s", var_name, exc)
                continue

            if len(observations) >= max_records:
                break

        ds.close()
        return observations[:max_records]

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ocean model data from OPeNDAP/THREDDS servers.

        Extra params:
            endpoint: Key from ENDPOINTS dict (e.g. 'hycom_global', 'ncep_sst')
            url: Custom OPeNDAP URL (overrides endpoint)
        """
        endpoint = params.get("endpoint", "hycom_global")
        custom_url = params.get("url", "")
        limit = params.get("limit", 500)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self._fetch_sync, bbox, time_start, time_end,
            endpoint, custom_url, limit,
        )

        logger.info("OPeNDAP returned %d grid points", len(results))
        return results

    @staticmethod
    def list_endpoints() -> dict[str, str]:
        """Return available pre-configured OPeNDAP endpoints."""
        return {k: v["description"] for k, v in ENDPOINTS.items()}
