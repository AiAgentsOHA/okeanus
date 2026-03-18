"""EU Blue Economy Report adapter.

The EU Blue Economy Report tracks the economic performance of
EU maritime sectors -- aquaculture, fisheries, offshore energy,
shipping, tourism, and more.

Data from Eurostat and DG MARE statistics. No auth required.

Data source: https://blue-economy-observatory.ec.europa.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Eurostat Statistics 1.0 JSON API (replaces broken SDMX 2.1 endpoint)
EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
# Fish catches dataset
FISH_CATCH_DS = "fish_ca_main"
# Maritime transport
TRANSPORT_DS = "mar_go_aa"

# EU coastal country centroids for geo-coding
_COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "AT": (14.55, 47.52), "BE": (4.47, 50.50), "BG": (25.49, 42.73),
    "HR": (15.98, 45.10), "CY": (33.43, 35.13), "CZ": (15.47, 49.82),
    "DK": (9.50, 56.26), "EE": (25.01, 58.60), "FI": (25.75, 61.92),
    "FR": (-1.60, 46.60), "DE": (10.45, 51.17), "EL": (23.73, 37.97),
    "HU": (19.50, 47.16), "IE": (-8.24, 53.41), "IT": (12.57, 41.87),
    "LV": (24.60, 56.88), "LT": (23.88, 55.17), "LU": (6.13, 49.82),
    "MT": (14.38, 35.94), "NL": (5.29, 52.13), "PL": (19.15, 51.92),
    "PT": (-8.22, 39.40), "RO": (24.97, 45.94), "SK": (19.70, 48.67),
    "SI": (14.99, 46.15), "ES": (-3.75, 40.46), "SE": (18.64, 60.13),
    "NO": (8.47, 60.47), "UK": (-3.44, 55.38), "IS": (-19.02, 64.96),
    "EU27_2020": (10.0, 50.0),
}


class EuBlueEconomyAdapter(BaseAdapter):
    """Connector for EU Blue Economy / Eurostat maritime data (no auth required).

    Returns EU maritime economic statistics from Eurostat Statistics 1.0 JSON API.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "eu_blue_economy"

    @property
    def source_url(self) -> str:
        return "https://blue-economy-observatory.ec.europa.eu/"

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
        """Fetch EU maritime economic statistics from Eurostat.

        Extra params:
            dataset: "fish_catch" (default), "maritime_transport"
            country: EU country code (e.g. "DE", "FR", "ES")
            limit: max records (default 500)
        """
        limit = params.get("limit", 500)
        dataset = params.get("dataset", "fish_catch")
        country = params.get("country")

        if dataset == "maritime_transport":
            ds_id = TRANSPORT_DS
        else:
            ds_id = FISH_CATCH_DS

        # Eurostat data lags 1-2 years; widen range to find published data
        start_yr = time_start.year
        end_yr = time_end.year
        if end_yr - start_yr < 3:
            start_yr = end_yr - 5

        url = f"{EUROSTAT_URL}/{ds_id}"

        # Statistics 1.0 API uses query-param filters (not path-based SDMX keys)
        api_params: dict[str, Any] = {
            "format": "JSON",
            "sinceTimePeriod": str(start_yr),
            "untilTimePeriod": str(end_yr),
            "lang": "EN",
        }
        if country:
            api_params["geo"] = country
        else:
            # Default to France to keep response small enough (avoid 413)
            api_params["geo"] = "FR"

        try:
            resp = await self._request("GET", url, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Eurostat maritime data fetch failed: %s", exc)
            return []

        # Parse Eurostat JSON-stat format
        observations: list[dict[str, Any]] = []

        dimensions = data.get("dimension", {})
        values = data.get("value", {})

        if not values:
            logger.warning("Eurostat returned no values for %s", ds_id)
            return []

        # Extract dimension metadata
        geo_dim = dimensions.get("geo", {}).get("category", {})
        geo_labels = geo_dim.get("label", {})
        geo_index = geo_dim.get("index", {})

        time_dim = dimensions.get("time", {}).get("category", {})
        time_labels = time_dim.get("label", {})
        time_index = time_dim.get("index", {})

        species_dim = dimensions.get("species", {}).get("category", {})
        species_labels = species_dim.get("label", {})
        species_index = species_dim.get("index", {})

        fishreg_dim = dimensions.get("fishreg", {}).get("category", {})
        fishreg_labels = fishreg_dim.get("label", {})

        # Dimension sizes for index calculation
        dim_ids = data.get("id", [])
        dim_sizes = data.get("size", [])

        for idx_str, value in list(values.items())[:limit]:
            try:
                val = float(value)
            except (ValueError, TypeError):
                continue

            # Resolve geo for coordinates
            geo_code = country or "FR"
            coords = _COUNTRY_COORDS.get(geo_code, (10.0, 50.0))

            observations.append({
                "obs_type": "economic",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": list(coords)},
                "source_id": f"eurostat-{ds_id}-{idx_str}",
                "source_name": "Eurostat / EU Blue Economy",
                "quality_score": 0.95,
                "payload": {
                    "dataset": ds_id,
                    "value": val,
                    "unit": "tonnes_live_weight" if ds_id == FISH_CATCH_DS else "thousand_tonnes",
                    "country": geo_code,
                    "index": idx_str,
                },
            })

        logger.info("EU Blue Economy returned %d records", len(observations))
        return observations
