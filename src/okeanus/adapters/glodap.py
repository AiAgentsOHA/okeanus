"""GLODAP adapter -- Global Ocean Data Analysis Project (ocean carbon).

GLODAPv2 is a synthesis of full-depth ocean carbon and biogeochemistry data
from 1108+ research cruises (1972-2023). Available via BCO-DMO ERDDAP as
tabledap dataset. No auth required.

The BCO-DMO dataset uses standard -180/+180 longitude convention.
GLODAP data is historical (cruises 2023 and earlier), so time-range
filtering is relaxed to cover the full dataset when no recent data exists.

Source: https://www.glodap.info/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ERDDAP_BASE = "https://erddap.bco-dmo.org/erddap/tabledap"
DATASET_ID = "bcodmo_dataset_957527_v2"


class GlodapAdapter(BaseAdapter):
    """Connector for GLODAPv2 ocean carbon data via BCO-DMO ERDDAP (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=90.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "glodap"

    @property
    def source_url(self) -> str:
        return "https://www.glodap.info/"

    @property
    def update_frequency(self) -> str:
        return "annual"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ocean carbon/biogeochemistry data from GLODAP.

        Extra params:
            depth_min: Min pressure in dbar (default 0)
            depth_max: Max pressure in dbar (default 6000)
            limit: Max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        # Core variables available in BCO-DMO GLODAP dataset
        variables = (
            "longitude,latitude,time,Cruise,Station,"
            "CTD_Pressure,CTDTEMP,CTD_Salinity,O2,"
            "Ship_DIC,Total_Alkalinity_Single_Step_method,"
            "NO3,PO4,Si"
        )

        # BCO-DMO dataset uses standard -180/+180 longitude -- no conversion
        # needed. Build ERDDAP constraint expression (NOT URL-encoded here;
        # httpx handles param encoding, but for ERDDAP tabledap the constraint
        # is part of the path, so we construct the full URL manually).
        constraints = (
            f"&latitude>={s}&latitude<={n}"
            f"&longitude>={w}&longitude<={e}"
        )

        # GLODAP data is historical. If time filter yields nothing,
        # omit time constraint to get whatever data exists in the bbox.
        # The dataset covers 2023 cruises, so a last-365-days window
        # from 2026 would miss everything.
        ts_start = time_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        ts_end = time_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        time_constraint = f"&time>={ts_start}&time<={ts_end}"

        # Build URL -- ERDDAP tabledap expects the query after the
        # dataset.format with NO double-encoding.
        query = f"{variables}{constraints}{time_constraint}"
        url = f"{ERDDAP_BASE}/{DATASET_ID}.json?{query}"

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception:
            # Retry without time constraint (data may predate the window)
            logger.info("GLODAP time-filtered query failed; retrying without time filter")
            query_no_time = f"{variables}{constraints}"
            url_no_time = f"{ERDDAP_BASE}/{DATASET_ID}.json?{query_no_time}"
            try:
                resp = await self._request("GET", url_no_time)
                data = resp.json()
            except Exception as exc:
                logger.error("GLODAP ERDDAP fetch failed: %s", exc)
                return []

        table = data.get("table", {})
        col_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        if not rows:
            logger.info("GLODAP returned 0 records")
            return []

        idx = {name: i for i, name in enumerate(col_names)}
        lat_i = idx.get("latitude")
        lon_i = idx.get("longitude")
        time_i = idx.get("time")

        if lat_i is None or lon_i is None:
            logger.warning("GLODAP missing lat/lon columns: %s", col_names)
            return []

        observations: list[dict[str, Any]] = []

        for row in rows:
            if len(observations) >= limit:
                break

            try:
                lat = float(row[lat_i])
                lon = float(row[lon_i])
            except (ValueError, TypeError, IndexError):
                continue

            # Parse timestamp
            try:
                ts_str = row[time_i] if time_i is not None else None
                if ts_str:
                    ts = datetime.fromisoformat(
                        str(ts_str).replace("Z", "+00:00")
                    )
                else:
                    continue
            except (ValueError, AttributeError):
                continue

            # Build payload from remaining columns
            payload: dict[str, Any] = {}
            for col_name, col_idx in idx.items():
                if col_name in ("latitude", "longitude", "time"):
                    continue
                val = row[col_idx]
                if val is not None:
                    payload[col_name.lower()] = val

            cruise = row[idx["Cruise"]] if "Cruise" in idx else ""
            station = row[idx["Station"]] if "Station" in idx else ""

            observations.append({
                "obs_type": "ocean_carbon",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"glodap-{cruise}-{station}-{len(observations)}",
                "source_name": "GLODAP",
                "quality_score": 0.95,
                "payload": payload,
            })

        logger.info("GLODAP returned %d records", len(observations))
        return observations
