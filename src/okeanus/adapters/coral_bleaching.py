"""Coral Bleaching Database adapter — 34,846 global bleaching records.

Van Woesik & Burkepile coral bleaching dataset hosted on BCO-DMO ERDDAP.
Contains bleaching percentage, SST anomalies, and environmental covariates
for reef sites worldwide (1980-2020). No auth required.

Source: https://www.bco-dmo.org/dataset/773466
ERDDAP: https://erddap.bco-dmo.org/erddap/tabledap/bcodmo_dataset_773466
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ERDDAP_URL = "https://erddap.bco-dmo.org/erddap/tabledap/bcodmo_dataset_773466.csv"


class CoralBleachingAdapter(BaseAdapter):
    """Connector for the global coral bleaching database (BCO-DMO ERDDAP)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "coral_bleaching"

    @property
    def source_url(self) -> str:
        return "https://erddap.bco-dmo.org/erddap/tabledap/bcodmo_dataset_773466"

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
        """Fetch coral bleaching records from BCO-DMO ERDDAP.

        Extra params:
            min_bleaching: Minimum bleaching percentage (default 0)
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        min_bleaching = params.get("min_bleaching", 0)
        w, s, e, n = bbox

        # ERDDAP tabledap query with spatial + variable selection
        fields = (
            "ID,latitude,longitude,Ocean,Country_Name,Ecoregion,"
            "Date,depth,Average_Bleaching,Temperature_Mean,SSTA,SSTA_DHW,ClimSST"
        )
        constraints = (
            f"&latitude>={s}&latitude<={n}"
            f"&longitude>={w}&longitude<={e}"
        )
        if min_bleaching > 0:
            constraints += f"&Average_Bleaching>={min_bleaching}"

        url = f"{ERDDAP_URL}?{fields}{constraints}&orderByLimit(%22ID,{limit}%22)"

        try:
            resp = await self._request("GET", url)
            text = resp.text
        except Exception as exc:
            logger.error("Coral bleaching ERDDAP fetch failed: %s", exc)
            return []

        observations: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text))

        # Skip the units row (second row in ERDDAP CSV)
        row_iter = iter(reader)
        try:
            first = next(row_iter)
            # Check if it's a units row (e.g. "degrees_north")
            if "degree" in str(first.get("latitude", "")).lower():
                first = next(row_iter)
            rows = [first]
        except StopIteration:
            return []

        for row in row_iter:
            rows.append(row)

        for row in rows:
            if len(observations) >= limit:
                break

            # Parse coordinates
            try:
                lat = float(row.get("latitude", ""))
                lon = float(row.get("longitude", ""))
            except (ValueError, TypeError):
                continue

            geometry = {"type": "Point", "coordinates": [lon, lat]}

            # Parse date (format: M/D/YYYY from ERDDAP)
            date_str = row.get("Date", "")
            ts = _parse_date(date_str)
            if ts is None:
                continue

            # Normalize timezone awareness for comparison
            ts_cmp = ts.replace(tzinfo=None) if ts.tzinfo else ts
            t_start = time_start.replace(tzinfo=None) if time_start.tzinfo else time_start
            t_end = time_end.replace(tzinfo=None) if time_end.tzinfo else time_end
            if ts_cmp < t_start or ts_cmp > t_end:
                continue

            # Parse bleaching percentage
            try:
                bleaching_pct = float(row.get("Average_Bleaching", 0))
            except (ValueError, TypeError):
                bleaching_pct = 0

            record_id = row.get("ID", "")
            country = row.get("Country_Name", "")
            ocean = row.get("Ocean", "")
            ecoregion = row.get("Ecoregion", "")

            observations.append({
                "obs_type": "coral_bleaching",
                "timestamp": ts,
                "geometry": geometry,
                "source_id": f"bleaching-{record_id}",
                "source_name": "Coral Bleaching Database (BCO-DMO)",
                "quality_score": 0.9,
                "payload": {
                    "record_id": record_id,
                    "country": country,
                    "ocean": ocean,
                    "ecoregion": ecoregion,
                    "bleaching_pct": bleaching_pct,
                    "depth_m": row.get("depth", ""),
                    "sst_mean_k": row.get("Temperature_Mean", ""),
                    "sst_climatology_c": row.get("ClimSST", ""),
                    "ssta": row.get("SSTA", ""),
                    "degree_heating_weeks": row.get("SSTA_DHW", ""),
                },
            })

        logger.info("Coral bleaching returned %d records", len(observations))
        return observations


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(s).strip()[:19], fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None
