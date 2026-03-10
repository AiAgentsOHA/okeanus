"""Copernicus Marine Environment Monitoring Service (CMEMS) adapter.

Retrieves physical and biogeochemical ocean data via the Copernicus Marine
Data Store REST API, returning dicts compatible with PhysicalObservationCreate.

Products used:
- GLOBAL_ANALYSISFORECAST_PHY_001_024  (physics: SST, currents, salinity)
- GLOBAL_ANALYSISFORECAST_BGC_001_028  (biogeochem: chlorophyll)
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

CMEMS_BASE_URL = "https://data-be-prd.marine.copernicus.eu/api"

# Dataset IDs
PHY_DATASET = "cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i"
CUR_DATASET = "cmems_mod_glo_phy-cur_anfc_0.083deg_PT6H-i"
BGC_DATASET = "cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m"


class CmemsAdapter(BaseAdapter):
    """Connector for the Copernicus Marine Data Store REST API."""

    def __init__(self, *, username: str = "", password: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._username = username
        self._password = password

    @property
    def source_name(self) -> str:
        return "cmems"

    @property
    def source_url(self) -> str:
        return CMEMS_BASE_URL

    @property
    def update_frequency(self) -> str:
        return "6-hourly"

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _auth_headers(self) -> dict[str, str]:
        """Return authorization headers if credentials are configured."""
        if self._username and self._password:
            import base64
            token = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
            return {"Authorization": f"Basic {token}"}
        return {}

    # ------------------------------------------------------------------
    # Internal: build subset request parameters
    # ------------------------------------------------------------------

    @staticmethod
    def _bbox_params(bbox: tuple[float, float, float, float]) -> dict[str, str]:
        return {
            "minimum_longitude": str(bbox[0]),
            "minimum_latitude": str(bbox[1]),
            "maximum_longitude": str(bbox[2]),
            "maximum_latitude": str(bbox[3]),
        }

    @staticmethod
    def _time_params(time_start: datetime, time_end: datetime) -> dict[str, str]:
        fmt = "%Y-%m-%dT%H:%M:%S"
        return {
            "start_datetime": time_start.strftime(fmt),
            "end_datetime": time_end.strftime(fmt),
        }

    async def _subset_request(
        self,
        dataset_id: str,
        variables: list[str],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Request a subset from the CMEMS data store and return raw JSON records."""
        url = f"{CMEMS_BASE_URL}/subset"
        params: dict[str, Any] = {
            "dataset_id": dataset_id,
            "variables": ",".join(variables),
            "format": "json",
            **self._bbox_params(bbox),
            **self._time_params(time_start, time_end),
        }
        try:
            resp = await self._request(
                "GET", url, params=params, headers=self._auth_headers(),
            )
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "values" in data:
                return data["values"]
            return [data] if data else []
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error("CMEMS subset request failed for %s: %s", dataset_id, exc)
            return []

    # ------------------------------------------------------------------
    # Helpers to convert raw CMEMS records to PhysicalObservation dicts
    # ------------------------------------------------------------------

    def _to_physical_dict(
        self,
        record: dict[str, Any],
        parameter: str,
        unit: str,
        value_key: str,
    ) -> dict[str, Any]:
        lon = record.get("longitude", record.get("lon", 0.0))
        lat = record.get("latitude", record.get("lat", 0.0))
        ts = record.get("time", record.get("datetime", datetime.now(UTC).isoformat()))
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.utcnow()
        value = record.get(value_key, record.get("value"))
        return {
            "timestamp": ts,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "source_id": str(uuid.uuid4()),
            "source_name": self.source_name,
            "parameter": parameter,
            "value": float(value) if value is not None else 0.0,
            "unit": unit,
            "depth_m": record.get("depth"),
        }

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_sst(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch sea surface temperature within bbox and time range."""
        records = await self._subset_request(
            PHY_DATASET, ["thetao"], bbox, time_start, time_end,
        )
        return [
            self._to_physical_dict(r, "SST", "degC", "thetao")
            for r in records
        ]

    async def get_currents(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch ocean current components (u, v) within bbox and time range."""
        records = await self._subset_request(
            CUR_DATASET, ["uo", "vo"], bbox, time_start, time_end,
        )
        results: list[dict[str, Any]] = []
        for r in records:
            if "uo" in r:
                results.append(self._to_physical_dict(r, "CURRENT_U", "m/s", "uo"))
            if "vo" in r:
                results.append(self._to_physical_dict(r, "CURRENT_V", "m/s", "vo"))
        return results

    async def get_chlorophyll(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch chlorophyll-a concentration within bbox and time range."""
        records = await self._subset_request(
            BGC_DATASET, ["chl"], bbox, time_start, time_end,
        )
        return [
            self._to_physical_dict(r, "SST", "mg/m3", "chl")  # reuses SST enum; payload clarifies
            for r in records
        ]

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
        variable = params.get("variable", "sst")
        if variable == "currents":
            return await self.get_currents(bbox, time_start, time_end)
        if variable == "chlorophyll":
            return await self.get_chlorophyll(bbox, time_start, time_end)
        return await self.get_sst(bbox, time_start, time_end)
