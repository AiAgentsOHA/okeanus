"""Climate indices adapter — ENSO, NAO, PDO, AMO, AO and more.

Fetches climate oscillation indices from NOAA PSL and CPC. These are
key drivers of ocean conditions (SST anomalies, storm patterns, etc.).

Sources:
- NOAA PSL: https://psl.noaa.gov/data/climateindices/list/
- NOAA CPC: https://www.cpc.ncep.noaa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Monthly climate index data URLs (NOAA PSL text format)
INDEX_URLS: dict[str, dict[str, str]] = {
    "nino34": {
        "url": "https://psl.noaa.gov/data/correlation/nina34.anom.data",
        "name": "Nino 3.4 SST Anomaly (ENSO)",
    },
    "nao": {
        "url": "https://psl.noaa.gov/data/correlation/nao.data",
        "name": "North Atlantic Oscillation",
    },
    "pdo": {
        "url": "https://psl.noaa.gov/data/correlation/pdo.data",
        "name": "Pacific Decadal Oscillation",
    },
    "amo": {
        "url": "https://psl.noaa.gov/data/correlation/amon.us.data",
        "name": "Atlantic Multidecadal Oscillation",
    },
    "ao": {
        "url": "https://psl.noaa.gov/data/correlation/ao.data",
        "name": "Arctic Oscillation",
    },
    "aao": {
        "url": "https://psl.noaa.gov/data/correlation/aao.data",
        "name": "Antarctic Oscillation",
    },
    "soi": {
        "url": "https://psl.noaa.gov/data/correlation/soi.data",
        "name": "Southern Oscillation Index",
    },
    "pna": {
        "url": "https://psl.noaa.gov/data/correlation/pna.data",
        "name": "Pacific/North American Pattern",
    },
    "oni": {
        "url": "https://psl.noaa.gov/data/correlation/oni.data",
        "name": "Oceanic Nino Index",
    },
    "whwp": {
        "url": "https://psl.noaa.gov/data/correlation/whwp.data",
        "name": "Western Hemisphere Warm Pool",
    },
    "tni": {
        "url": "https://psl.noaa.gov/data/correlation/tni.data",
        "name": "Trans-Nino Index",
    },
    "mei": {
        "url": "https://psl.noaa.gov/enso/mei/data/meiv2.data",
        "name": "Multivariate ENSO Index v2",
    },
}


class ClimateIndicesAdapter(BaseAdapter):
    """Connector for NOAA climate oscillation indices (ENSO, NAO, PDO, etc.)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "climate_indices"

    @property
    def source_url(self) -> str:
        return "https://psl.noaa.gov/data/climateindices/list/"

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
        """Fetch climate index time series.

        Extra params:
            indices: List of index keys (default: all)
            limit: Max records per index (default 100)
        """
        limit = params.get("limit", 100)
        index_keys = params.get("indices", list(INDEX_URLS.keys()))

        observations: list[dict[str, Any]] = []

        for key in index_keys:
            if key not in INDEX_URLS:
                continue

            info = INDEX_URLS[key]
            try:
                resp = await self._request("GET", info["url"])
                text = resp.text
            except Exception as exc:
                logger.error("Climate index %s fetch failed: %s", key, exc)
                continue

            records = _parse_psl_text(text, key, info["name"], time_start, time_end)
            observations.extend(records[:limit])

        observations.sort(key=lambda x: x["timestamp"], reverse=True)
        return observations[:limit]


def _parse_psl_text(
    text: str,
    index_key: str,
    index_name: str,
    time_start: datetime,
    time_end: datetime,
) -> list[dict[str, Any]]:
    """Parse NOAA PSL fixed-width text format.

    Format: first line is header with start/end years,
    then rows of: YEAR  JAN  FEB  MAR  APR  MAY  JUN  JUL  AUG  SEP  OCT  NOV  DEC
    Missing values are typically -99.99 or -999.00.
    """
    lines = text.strip().split("\n")
    if len(lines) < 3:
        return []

    observations: list[dict[str, Any]] = []
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) < 2:
            continue

        try:
            year = int(float(parts[0]))
        except (ValueError, IndexError):
            continue

        if year < 1800 or year > 2100:
            continue

        for month_idx, val_str in enumerate(parts[1:13], start=1):
            try:
                value = float(val_str)
            except ValueError:
                continue

            # Skip missing values
            if value <= -99.0 or value >= 999.0:
                continue

            ts = datetime(year, month_idx, 15, tzinfo=timezone.utc)

            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "climate_index",
                "timestamp": ts,
                "geometry": None,  # Global indices, no specific location
                "source_id": f"climate-{index_key}-{year}-{month_idx:02d}",
                "source_name": "NOAA PSL",
                "quality_score": 1.0,
                "payload": {
                    "index_name": index_name,
                    "index_key": index_key,
                    "value": value,
                    "year": year,
                    "month": month_idx,
                    "month_name": month_names[month_idx - 1],
                },
            })

    return observations
