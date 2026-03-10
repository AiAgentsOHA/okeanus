"""ECMWF Open Data adapter — global weather and wave forecasts.

Free access to ECMWF's HRES/ENS deterministic and ensemble forecasts
via the ``ecmwf-opendata`` Python package. No auth required.

Requires:  pip install ecmwf-opendata
Docs:      https://github.com/ecmwf/ecmwf-opendata
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class EcmwfOpenAdapter(BaseAdapter):
    """Connector for ECMWF open forecast data (no auth required).

    Downloads GRIB2 forecast fields and converts surface grid points
    to observation dicts. Requires ``ecmwf-opendata`` and ``cfgrib``.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ecmwf_open"

    @property
    def source_url(self) -> str:
        return "https://data.ecmwf.int/forecasts/"

    @property
    def update_frequency(self) -> str:
        return "6-hourly"

    def _fetch_sync(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        variable: str,
        max_records: int,
    ) -> list[dict[str, Any]]:
        """Synchronous ECMWF fetch — runs in executor."""
        try:
            from ecmwf.opendata import Client
        except ImportError:
            logger.error("ecmwf-opendata not installed: pip install ecmwf-opendata")
            return []

        w, s, e, n = bbox

        client = Client(source="ecmwf")

        # Map friendly names to ECMWF parameter codes
        param_map = {
            "wind": "10u/10v",
            "wave": "swh/mwp/mwd",
            "pressure": "msl",
            "temperature": "2t",
            "sst": "sst",
            "precipitation": "tp",
        }
        param = param_map.get(variable, variable)

        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".grib2") as tmp:
                client.retrieve(
                    step=0,
                    type="fc",
                    param=param,
                    target=tmp.name,
                    area=[n, w, s, e],  # ECMWF uses N/W/S/E
                )

                # Parse GRIB2 with cfgrib + xarray
                try:
                    import xarray as xr
                    ds = xr.open_dataset(tmp.name, engine="cfgrib")
                except ImportError:
                    logger.error("cfgrib not installed: pip install cfgrib")
                    return []

                # Convert grid to observation dicts
                observations: list[dict[str, Any]] = []
                for var_name in ds.data_vars:
                    da = ds[var_name].compute()
                    df = da.to_dataframe().reset_index().dropna(subset=[var_name])

                    if len(df) > max_records:
                        df = df.sample(n=max_records, random_state=42)

                    for _, row in df.iterrows():
                        lon = float(row.get("longitude", 0))
                        lat = float(row.get("latitude", 0))
                        ts = row.get("time", time_start)
                        if hasattr(ts, "to_pydatetime"):
                            ts = ts.to_pydatetime()

                        observations.append({
                            "obs_type": "physical",
                            "timestamp": ts,
                            "geometry": {"type": "Point", "coordinates": [lon, lat]},
                            "source_id": f"ecmwf-{var_name}-{lat:.2f}-{lon:.2f}",
                            "source_name": "ECMWF Open Data",
                            "quality_score": 0.95,
                            "payload": {
                                "parameter": var_name,
                                "value": float(row[var_name]),
                                "step_hours": int(row.get("step", 0)) if "step" in row.index else 0,
                                "forecast_type": "HRES",
                            },
                        })

                    if len(observations) >= max_records:
                        break

                return observations[:max_records]

        except Exception as exc:
            logger.error("ECMWF fetch failed: %s", exc)
            return []

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ECMWF forecast data within bbox.

        Extra params:
            variable: 'wind', 'wave', 'pressure', 'temperature', 'sst',
                      'precipitation', or raw ECMWF param code
        """
        variable = params.get("variable", "wind")
        limit = params.get("limit", 500)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self._fetch_sync, bbox, time_start, variable, limit,
        )

        logger.info("ECMWF returned %d forecast points", len(results))
        return results
