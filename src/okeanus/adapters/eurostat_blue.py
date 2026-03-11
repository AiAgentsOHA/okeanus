"""Eurostat Blue Economy adapter — EU maritime/fisheries statistics.

GVA, employment, turnover for maritime transport, coastal tourism,
fisheries, aquaculture, offshore energy, shipbuilding across EU-27.

API docs: https://wikis.ec.europa.eu/display/EUROSTATHELP/API+SDMX+2.1
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1"

# Key dataset codes for blue economy
BLUE_DATASETS = {
    "fish_ca_main": "Catches — major fishing areas",
    "fish_aq_q": "Aquaculture production (quantity)",
    "fish_aq_v": "Aquaculture production (value)",
    "fish_ld_main": "Landings of fishery products",
    "fish_fleet_gp": "Fishing fleet — number/tonnage",
    "mar_go_qm": "Goods transported by sea (quarterly)",
    "mar_mp_aa": "Main ports — gross weight by direction",
    "mar_pa_aa": "Passengers embarked/disembarked",
    "tour_occ_nim": "Nights spent at tourist accommodation — coastal",
    "sbs_sc_ind_r2": "Maritime industry SBS statistics",
}


class EurostatBlueAdapter(BaseAdapter):
    """Connector for Eurostat SDMX API — EU blue economy (no auth).

    Returns fisheries, maritime transport, and coastal tourism statistics
    for EU member states.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "eurostat_blue"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "quarterly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch Eurostat blue economy data.

        Extra params:
            dataset: Eurostat dataset code (default: fish_ca_main)
            country: ISO2 country code (e.g. 'FR', 'ES')
            limit: max records (default: 500)
        """
        dataset = params.get("dataset", "fish_ca_main")
        country = params.get("country")
        limit = params.get("limit", 500)

        year_start = time_start.year
        year_end = time_end.year

        # Build SDMX REST query
        # Filter key: freq.geo.species.fishreg...
        geo_filter = country.upper() if country else ""
        time_filter = f"startPeriod={year_start}&endPeriod={year_end}"

        url = f"{BASE_URL}/data/{dataset}"
        query: dict[str, Any] = {
            "format": "JSON",
            "startPeriod": str(year_start),
            "endPeriod": str(year_end),
            "lang": "en",
        }
        if geo_filter:
            query["geo"] = geo_filter

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("Eurostat fetch %s failed: %s", dataset, exc)
            return []

        observations: list[dict[str, Any]] = []
        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        # SDMX JSON response structure
        dimension = data.get("dimension", {})
        values_data = data.get("value", {})
        sizes = data.get("size", [])

        # Extract geo and time dimensions
        geo_dim = dimension.get("geo", {}).get("category", {})
        geo_labels = geo_dim.get("label", {})
        time_dim = dimension.get("time", {}).get("category", {})
        time_labels = time_dim.get("label", {})

        if not values_data:
            # Fallback: try dataset/value structure
            ds = data.get("dataSets", [{}])
            if ds:
                series = ds[0].get("series", {}) if ds else {}
                for key, val in series.items():
                    for obs_key, obs_val in val.get("observations", {}).items():
                        if not obs_val:
                            continue
                        observations.append({
                            "obs_type": "economic",
                            "timestamp": datetime(year_start, 1, 1),
                            "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                            "source_id": f"eurostat-{dataset}-{key}-{obs_key}",
                            "source_name": "Eurostat",
                            "quality_score": 0.95,
                            "payload": {
                                "dataset": dataset,
                                "dataset_name": BLUE_DATASETS.get(dataset, dataset),
                                "series_key": key,
                                "value": obs_val[0] if isinstance(obs_val, list) else obs_val,
                            },
                        })
        else:
            # JSON-stat style
            idx = 0
            for geo_code, geo_label in geo_labels.items():
                for time_code, time_label in time_labels.items():
                    str_idx = str(idx)
                    idx += 1
                    if str_idx not in values_data:
                        continue

                    try:
                        yr = int(time_code[:4])
                        ts = datetime(yr, 1, 1)
                    except (ValueError, TypeError):
                        continue

                    observations.append({
                        "obs_type": "economic",
                        "timestamp": ts,
                        "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                        "source_id": f"eurostat-{dataset}-{geo_code}-{time_code}",
                        "source_name": "Eurostat",
                        "quality_score": 0.95,
                        "payload": {
                            "dataset": dataset,
                            "dataset_name": BLUE_DATASETS.get(dataset, dataset),
                            "country_code": geo_code,
                            "country_name": geo_label,
                            "period": time_code,
                            "value": values_data[str_idx],
                        },
                    })

        observations = observations[:limit]
        logger.info("Eurostat %s returned %d observations", dataset, len(observations))
        return observations
