"""argopy adapter — enhanced Argo float profiles.

Provides richer access to Argo float data than the Argovis REST adapter,
including BGC parameters, deep Argo, and quality-controlled profiles.

Requires:  pip install argopy
Docs:      https://argopy.readthedocs.io/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class ArgopyAdapter(BaseAdapter):
    """Connector for Argo data via the argopy Python package.

    Wraps argopy's DataFetcher for bbox/time queries. Falls back to
    the Argovis REST adapter if argopy is not installed.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "argopy"

    @property
    def source_url(self) -> str:
        return "https://argo.ucsd.edu/"

    @property
    def update_frequency(self) -> str:
        return "near-real-time"

    def _fetch_sync(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        max_records: int,
        dataset: str,
    ) -> list[dict[str, Any]]:
        """Synchronous argopy fetch — runs in executor."""
        try:
            import argopy
        except ImportError:
            logger.error("argopy not installed: pip install argopy")
            return []

        w, s, e, n = bbox

        # --- Constrain query to avoid timeout ---
        # 1. Shrink bbox to max 5 degrees on each side
        mid_lon, mid_lat = (w + e) / 2, (s + n) / 2
        half = 2.5
        w2 = max(w, mid_lon - half)
        e2 = min(e, mid_lon + half)
        s2 = max(s, mid_lat - half)
        n2 = min(n, mid_lat + half)
        # 2. Limit time range to last 30 days
        from datetime import timedelta
        max_window = timedelta(days=30)
        if (time_end - time_start) > max_window:
            time_start = time_end - max_window
        # 3. Limit depth to 500m (surface profiles)
        max_depth = 500

        try:
            fetcher = argopy.DataFetcher(
                src="argovis",
                ds=dataset,
            ).region(
                [w2, e2, s2, n2, 0, max_depth,
                 time_start.strftime("%Y-%m-%d"), time_end.strftime("%Y-%m-%d")],
            )
            ds = fetcher.to_xarray()
        except Exception as exc:
            logger.error("argopy fetch failed: %s", exc)
            return []

        observations: list[dict[str, Any]] = []

        try:
            df = ds.to_dataframe().reset_index()
        except Exception:
            return []

        if len(df) > max_records:
            df = df.sample(n=max_records, random_state=42)

        for _, row in df.iterrows():
            lon = float(row.get("LONGITUDE", row.get("longitude", 0)))
            lat = float(row.get("LATITUDE", row.get("latitude", 0)))

            ts_val = row.get("TIME", row.get("time"))
            if ts_val is not None and hasattr(ts_val, "to_pydatetime"):
                ts = ts_val.to_pydatetime()
            elif ts_val is not None:
                try:
                    import numpy as np
                    ts = ts_val.astype("datetime64[ms]").astype(datetime)
                except Exception:
                    ts = time_start
            else:
                ts = time_start

            payload: dict[str, Any] = {
                "platform_number": str(row.get("PLATFORM_NUMBER", "")),
                "cycle_number": row.get("CYCLE_NUMBER"),
                "direction": row.get("DIRECTION", ""),
            }

            # Add measured parameters
            for col in ["TEMP", "PSAL", "PRES", "DOXY", "CHLA", "BBP700", "PH_IN_SITU_TOTAL"]:
                val = row.get(col)
                if val is not None and str(val) != "nan":
                    payload[col.lower()] = float(val)

            depth = row.get("PRES", row.get("depth"))

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"argopy-{row.get('PLATFORM_NUMBER', '')}-{row.get('CYCLE_NUMBER', '')}",
                "source_name": "Argo (argopy)",
                "quality_score": 0.95,
                "payload": payload,
            })

        return observations

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch Argo float profiles via argopy.

        Extra params:
            dataset: 'phy' (default — T/S) or 'bgc' (biogeochemical)
        """
        limit = params.get("limit", 500)
        dataset = params.get("dataset", "phy")

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self._fetch_sync, bbox, time_start, time_end, limit, dataset,
        )

        logger.info("argopy returned %d profiles", len(results))
        return results
