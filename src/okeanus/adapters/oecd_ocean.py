"""OECD Ocean Economy Database adapter.

Ocean-based industries value-added, employment, and innovation metrics
across 140+ countries and 25+ years.

API: SDMX REST 3.0 at sdmx.oecd.org.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://sdmx.oecd.org/public/rest/data"

# Key OECD ocean/maritime datasets
DATASETS = {
    "FISH_LAND": "Fish landings",
    "FISH_AQUA": "Aquaculture production",
    "FISH_TRADE": "Fish trade",
    "FISH_EMPL": "Fisheries employment",
    "FISH_FLEET": "Fishing fleet",
    "MTC": "Maritime Transport Costs",
    "SNA_TABLE1": "GDP by activity (for ocean sectors extraction)",
    "GREEN_GROWTH": "Green growth indicators (ocean subset)",
}


class OecdOceanAdapter(BaseAdapter):
    """Connector for OECD SDMX 3.0 API — ocean economy data (no auth).

    Returns fisheries, maritime transport, and ocean-industry statistics
    for OECD and partner countries.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "oecd_ocean"

    @property
    def source_url(self) -> str:
        return "https://sdmx.oecd.org/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch OECD ocean economy statistics.

        Extra params:
            dataset: OECD dataset code (default: FISH_LAND)
            country: ISO3 code (e.g. 'NOR', 'JPN') or 'all'
            measure: measure dimension filter
            limit: max records (default: 500)
        """
        dataset = params.get("dataset", "FISH_LAND")
        country = params.get("country", "")
        measure = params.get("measure", "")
        limit = params.get("limit", 500)
        year_start = time_start.year
        year_end = time_end.year

        # SDMX 3.0 URL structure
        key = f"{country}.{measure}" if measure else f"{country}"
        url = f"{BASE_URL}/OECD.TAD.ARP,DSD_{dataset}@DF_{dataset}/{key}"

        query: dict[str, Any] = {
            "startPeriod": str(year_start),
            "endPeriod": str(year_end),
            "dimensionAtObservation": "AllDimensions",
        }
        headers = {"Accept": "application/vnd.sdmx.data+json;version=2.0.0"}

        try:
            resp = await self._request("GET", url, params=query, headers=headers)
            data = resp.json()
        except Exception as exc:
            logger.warning("OECD SDMX 3.0 failed for %s: %s, trying 2.1 fallback", dataset, exc)
            return await self._fetch_sdmx21(dataset, country, year_start, year_end, limit)

        observations: list[dict[str, Any]] = []

        # Parse SDMX-JSON 2.0 structure
        datasets = data.get("dataSets", data.get("data", []))
        if isinstance(datasets, list) and datasets:
            ds = datasets[0]
        elif isinstance(datasets, dict):
            ds = datasets
        else:
            return []

        series = ds.get("series", ds.get("observations", {}))
        structure = data.get("structure", {})
        dims = structure.get("dimensions", {})

        for key, val in (series.items() if isinstance(series, dict) else []):
            obs_map = val.get("observations", {}) if isinstance(val, dict) else {}

            for obs_key, obs_val in obs_map.items():
                if not obs_val:
                    continue

                value = obs_val[0] if isinstance(obs_val, list) else obs_val

                try:
                    val_f = float(value)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": datetime(year_start, 1, 1),
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"oecd-{dataset}-{key}-{obs_key}",
                    "source_name": "OECD",
                    "quality_score": 0.95,
                    "payload": {
                        "dataset": dataset,
                        "dataset_name": DATASETS.get(dataset, dataset),
                        "series_key": key,
                        "value": val_f,
                        "country": country or "all",
                    },
                })

        observations = observations[:limit]
        logger.info("OECD %s returned %d observations", dataset, len(observations))
        return observations

    async def _fetch_sdmx21(
        self,
        dataset: str,
        country: str,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback to OECD SDMX 2.1 endpoint."""
        url = f"https://stats.oecd.org/SDMX-JSON/data/{dataset}/{country or 'all'}/all"
        query = {
            "startTime": str(year_start),
            "endTime": str(year_end),
            "json-lang": "en",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("OECD 2.1 fallback %s failed: %s", dataset, exc)
            return []

        observations: list[dict[str, Any]] = []
        datasets = data.get("dataSets", [{}])
        if not datasets:
            return []

        series = datasets[0].get("series", {})
        for key, val in series.items():
            for obs_key, obs_val in val.get("observations", {}).items():
                if not obs_val:
                    continue

                yr = year_start + int(obs_key)
                if yr > year_end:
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": datetime(yr, 1, 1),
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"oecd21-{dataset}-{key}-{yr}",
                    "source_name": "OECD",
                    "quality_score": 0.93,
                    "payload": {
                        "dataset": dataset,
                        "dataset_name": DATASETS.get(dataset, dataset),
                        "series_key": key,
                        "year": yr,
                        "value": obs_val[0] if isinstance(obs_val, list) else obs_val,
                        "country": country or "all",
                    },
                })

        return observations[:limit]
