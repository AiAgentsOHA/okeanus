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

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

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

        # JSON-stat statistics API (v1.0)
        # Eurostat data lags 1-2 years; widen range to find published data
        if year_end - year_start < 3:
            year_start = year_end - 5
        geo_filter = country.upper() if country else ""

        url = f"{BASE_URL}/{dataset}"
        query: dict[str, Any] = {
            "format": "JSON",
            "lang": "en",
            "sinceTimePeriod": str(year_start),
            "untilTimePeriod": str(year_end),
        }
        if geo_filter:
            query["geo"] = geo_filter
        else:
            # Without a geo filter the response can be huge (413).
            # Default to Germany to keep response small.
            query["geo"] = "DE"

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

        # JSON-stat 2.0 response: top-level has "dimension", "value", "id", "size"
        values_data = data.get("value", {})
        if not values_data:
            logger.warning("Eurostat %s: no values in response", dataset)
            return []

        dimension = data.get("dimension", {})
        dim_ids = data.get("id", [])  # ordered list of dimension names
        sizes = data.get("size", [])  # sizes of each dimension

        # Build ordered list of dimension categories
        dim_categories: list[list[str]] = []
        dim_labels_map: dict[str, dict[str, str]] = {}
        for dim_name in dim_ids:
            dim_info = dimension.get(dim_name, {})
            cat = dim_info.get("category", {})
            index = cat.get("index", {})
            labels = cat.get("label", {})
            dim_labels_map[dim_name] = labels
            # index can be dict {code: position} or list [code, ...]
            if isinstance(index, dict):
                sorted_codes = sorted(index.keys(), key=lambda k: index[k])
            elif isinstance(index, list):
                sorted_codes = index
            else:
                sorted_codes = list(labels.keys())
            dim_categories.append(sorted_codes)

        # Find positions of geo and time dimensions
        geo_pos = None
        time_pos = None
        for i, dim_name in enumerate(dim_ids):
            if dim_name == "geo":
                geo_pos = i
            elif dim_name == "time":
                time_pos = i

        # Iterate through flat value index and decode dimensions
        for str_idx, value in values_data.items():
            idx = int(str_idx)
            # Decode flat index to dimension positions
            coords: list[int] = []
            remaining = idx
            for s in reversed(sizes):
                coords.append(remaining % s)
                remaining //= s
            coords.reverse()

            geo_code = ""
            geo_label = ""
            time_code = ""
            if geo_pos is not None and geo_pos < len(coords):
                pos = coords[geo_pos]
                cats = dim_categories[geo_pos]
                if pos < len(cats):
                    geo_code = cats[pos]
                    geo_label = dim_labels_map.get("geo", {}).get(geo_code, geo_code)
            if time_pos is not None and time_pos < len(coords):
                pos = coords[time_pos]
                cats = dim_categories[time_pos]
                if pos < len(cats):
                    time_code = cats[pos]

            try:
                yr = int(time_code[:4])
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                ts = datetime(year_start, 1, 1)

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
                    "value": value,
                },
            })

        observations = observations[:limit]
        logger.info("Eurostat %s returned %d observations", dataset, len(observations))
        return observations
