"""Copernicus Marine Environment Monitoring Service (CMEMS) adapter.

Retrieves physical and biogeochemical ocean data via the official
``copernicusmarine`` Python toolbox, returning dicts compatible with
PhysicalObservationCreate.

Products used:
- GLOBAL_ANALYSISFORECAST_PHY_001_024  (physics: SST, currents, salinity)
- GLOBAL_ANALYSISFORECAST_BGC_001_028  (biogeochem: chlorophyll)

Requires:  pip install copernicusmarine
Auth:      CMEMS_USERNAME + CMEMS_PASSWORD env vars (or pass to constructor)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

import numpy as np

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Dataset IDs (same as before — these are the CMEMS catalog identifiers)
PHY_SST_DATASET = "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i"
PHY_CUR_DATASET = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
BGC_DATASET = "cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m"


class CmemsAdapter(BaseAdapter):
    """Connector for Copernicus Marine data via the copernicusmarine toolbox."""

    def __init__(self, *, username: str = "", password: str = "", **kw: Any) -> None:
        super().__init__(requests_per_second=0.5, **kw)
        import os
        self._username = username or os.environ.get("CMEMS_USERNAME", "")
        self._password = password or os.environ.get("CMEMS_PASSWORD", "")

    @property
    def source_name(self) -> str:
        return "cmems"

    @property
    def source_url(self) -> str:
        return "https://data.marine.copernicus.eu"

    @property
    def update_frequency(self) -> str:
        return "6-hourly"

    # ------------------------------------------------------------------
    # Internal: open xarray Dataset via copernicusmarine
    # ------------------------------------------------------------------

    def _open_dataset_sync(
        self,
        dataset_id: str,
        variables: list[str],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> Any:
        """Synchronous wrapper around copernicusmarine.open_dataset.

        Returns an xarray.Dataset (lazy-loaded).
        """
        import copernicusmarine

        w, s, e, n = bbox
        return copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            variables=variables,
            minimum_longitude=w,
            minimum_latitude=s,
            maximum_longitude=e,
            maximum_latitude=n,
            start_datetime=time_start.isoformat(),
            end_datetime=time_end.isoformat(),
            minimum_depth=0.0,
            maximum_depth=1.0,  # surface only
            username=self._username or None,
            password=self._password or None,
        )

    async def _load_dataset(
        self,
        dataset_id: str,
        variables: list[str],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> Any:
        """Async wrapper — runs the blocking copernicusmarine call in a thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._open_dataset_sync,
            dataset_id,
            variables,
            bbox,
            time_start,
            time_end,
        )

    # ------------------------------------------------------------------
    # Convert xarray Dataset to observation dicts
    # ------------------------------------------------------------------

    @staticmethod
    def _dataset_to_observations(
        ds: Any,
        variable: str,
        parameter: str,
        unit: str,
        max_records: int = 500,
    ) -> list[dict[str, Any]]:
        """Convert an xarray Dataset into a list of observation dicts.

        Samples up to ``max_records`` grid points to avoid huge payloads.
        """
        if variable not in ds:
            logger.warning(
                "Variable %s not found in dataset (available: %s)",
                variable, list(ds.data_vars),
            )
            return []

        da = ds[variable]

        # Compute into memory (small surface subset)
        da = da.compute()

        # Flatten to a dataframe for easy iteration
        df = da.to_dataframe().reset_index().dropna(subset=[variable])

        if df.empty:
            return []

        # Sample if too large
        if len(df) > max_records:
            df = df.sample(n=max_records, random_state=42)

        observations: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            lon = float(row.get("longitude", row.get("lon", 0.0)))
            lat = float(row.get("latitude", row.get("lat", 0.0)))
            ts = row.get("time", None)
            if ts is not None and hasattr(ts, "isoformat"):
                ts = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts
            elif ts is not None and isinstance(ts, np.datetime64):
                ts = ts.astype("datetime64[ms]").astype(datetime)
            else:
                ts = datetime.utcnow()

            val = float(row[variable])
            depth = float(row.get("depth", 0.0)) if "depth" in row.index else None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": str(uuid.uuid4()),
                "source_name": "CMEMS",
                "parameter": parameter,
                "value": val,
                "unit": unit,
                "payload": {
                    "parameter": parameter,
                    "value": val,
                    "unit": unit,
                    "depth_m": depth,
                },
            })

        return observations

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_sst(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch sea surface temperature within bbox and time range."""
        ds = await self._load_dataset(PHY_SST_DATASET, ["thetao"], bbox, time_start, time_end)
        return self._dataset_to_observations(ds, "thetao", "SST", "degC", max_records=limit)

    async def get_currents(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch ocean surface currents (u, v) within bbox and time range."""
        ds = await self._load_dataset(PHY_CUR_DATASET, ["uo", "vo"], bbox, time_start, time_end)
        results: list[dict[str, Any]] = []
        half = limit // 2
        results.extend(
            self._dataset_to_observations(ds, "uo", "CURRENT_U", "m/s", half),
        )
        results.extend(
            self._dataset_to_observations(ds, "vo", "CURRENT_V", "m/s", half),
        )
        return results

    async def get_chlorophyll(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch chlorophyll-a concentration within bbox and time range."""
        ds = await self._load_dataset(BGC_DATASET, ["chl"], bbox, time_start, time_end)
        return self._dataset_to_observations(ds, "chl", "CHL_A", "mg/m3", max_records=limit)

    # ------------------------------------------------------------------
    # BaseAdapter.fetch implementation
    # ------------------------------------------------------------------

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch SST observations by default; pass ``variable`` to override."""
        if not self._username or not self._password:
            logger.error(
                "CMEMS requires credentials"
                " (set CMEMS_USERNAME / CMEMS_PASSWORD)",
            )
            return []

        variable = params.get("variable", "sst")
        limit = params.get("limit", 500)

        try:
            if variable == "currents":
                return await self.get_currents(bbox, time_start, time_end, limit)
            if variable == "chlorophyll":
                return await self.get_chlorophyll(bbox, time_start, time_end, limit)
            return await self.get_sst(bbox, time_start, time_end, limit)
        except Exception as exc:
            logger.error("CMEMS fetch failed: %s", exc)
            return []
