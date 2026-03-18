"""EUMOFA (European Market Observatory for Fisheries and Aquaculture) adapter.

108 species, first-sale to consumer prices across EU-27 + 4 countries.

EUMOFA itself does NOT expose a public REST API — it is a Liferay CMS portal.
This adapter uses the **Eurostat fish_ca_main** dataset (EU fisheries capture
production by species, fishing region, and country) as a machine-readable
proxy.  The underlying data originates from the same FAO/Eurostat pipeline
that feeds EUMOFA dashboards.

Eurostat JSON API docs:
  https://wikis.ec.europa.eu/display/EUROSTAT/API+SDMX+2.1

No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

_EUROSTAT_API = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
_DATASET = "fish_ca_main"


class EumofaAdapter(BaseAdapter):
    """Connector for EU fisheries data via Eurostat fish_ca_main.

    Provides annual capture-fisheries production (tonnes live weight)
    by species, fishing region, and EU country.  Backed by the Eurostat
    SDMX JSON API — no auth required.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "eumofa"

    @property
    def source_url(self) -> str:
        return "https://www.eumofa.eu/"

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
        """Fetch EU fisheries capture production from Eurostat.

        Extra params:
            geo: Eurostat country code (default 'EU27_2020')
            species: species filter code (default all top-level)
            limit: max records (default 200)
        """
        limit = params.get("limit", 200)
        geo = params.get("geo", "EU27_2020")

        start_year = time_start.year
        end_year = time_end.year
        # Eurostat fisheries data lags 2-3 years; widen window
        effective_start = max(start_year - 5, 2000)

        url = f"{_EUROSTAT_API}/{_DATASET}"
        api_params: dict[str, Any] = {
            "format": "JSON",
            "lang": "en",
            "sinceTimePeriod": str(effective_start),
            "untilTimePeriod": str(end_year),
            "geo": geo,
        }

        try:
            resp = await self._request("GET", url, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("EUMOFA (Eurostat) fetch failed: %s", exc)
            return []

        values = data.get("value", {})
        if not values:
            logger.warning("EUMOFA: Eurostat returned no values")
            return []

        # Parse dimension metadata
        dims = data.get("dimension", {})
        id_order = data.get("id", [])
        sizes = data.get("size", [])

        def _dim_labels(name: str) -> dict[str, str]:
            d = dims.get(name, {})
            cat = d.get("category", {})
            idx = cat.get("index", {})
            lbl = cat.get("label", {})
            return {str(v): lbl.get(k, k) for k, v in idx.items()}

        species_labels = _dim_labels("species")
        region_labels = _dim_labels("fishreg")
        time_labels = _dim_labels("time")
        geo_labels = _dim_labels("geo")

        # Build index multipliers for flat value lookup
        multipliers: list[int] = []
        for i in range(len(sizes)):
            m = 1
            for j in range(i + 1, len(sizes)):
                m *= sizes[j]
            multipliers.append(m)

        dim_indices: dict[str, dict[str, int]] = {}
        for name in id_order:
            d = dims.get(name, {})
            idx = d.get("category", {}).get("index", {})
            dim_indices[name] = {k: v for k, v in idx.items()}

        observations: list[dict[str, Any]] = []

        # Iterate over species x region x time combinations
        species_idx = dim_indices.get("species", {})
        region_idx = dim_indices.get("fishreg", {})
        time_idx = dim_indices.get("time", {})
        geo_idx_map = dim_indices.get("geo", {})
        freq_idx = dim_indices.get("freq", {})
        unit_idx = dim_indices.get("unit", {})

        # Get the first (usually only) freq and unit indices
        freq_i = list(freq_idx.values())[0] if freq_idx else 0
        unit_i = list(unit_idx.values())[0] if unit_idx else 0
        geo_i = list(geo_idx_map.values())[0] if geo_idx_map else 0

        # Only iterate top-level species to keep output manageable
        top_species = {k: v for k, v in species_idx.items()
                       if k.startswith("TOTAL") or k in (
                           "FW_FIS", "SHEL", "FIN", "CRU", "MOL")}
        if not top_species:
            # fallback: take first 20 species
            top_species = dict(list(species_idx.items())[:20])

        for sp_code, sp_i in top_species.items():
            for reg_code, reg_i in region_idx.items():
                for yr_code, yr_i in time_idx.items():
                    try:
                        year = int(yr_code)
                    except ValueError:
                        continue
                    if year < effective_start or year > end_year:
                        continue

                    # Compute flat index based on dimension order
                    idx_map = {
                        "freq": freq_i, "species": sp_i, "fishreg": reg_i,
                        "unit": unit_i, "geo": geo_i, "time": yr_i,
                    }
                    flat = 0
                    for pos, dim_name in enumerate(id_order):
                        flat += idx_map.get(dim_name, 0) * multipliers[pos]

                    val = values.get(str(flat))
                    if val is None or val == 0:
                        continue

                    ts = datetime(year, 7, 1, tzinfo=timezone.utc)

                    observations.append({
                        "obs_type": "fisheries",
                        "timestamp": ts,
                        "geometry": None,
                        "source_id": f"eumofa-{geo}-{sp_code}-{reg_code}-{year}",
                        "source_name": "EUMOFA",
                        "quality_score": 0.9,
                        "payload": {
                            "year": year,
                            "catch_tonnes": float(val),
                            "species": sp_code,
                            "species_name": species_labels.get(str(sp_i), sp_code),
                            "fishing_region": reg_code,
                            "region_name": region_labels.get(str(reg_i), reg_code),
                            "country": geo,
                            "country_name": geo_labels.get(str(geo_i), geo),
                            "unit": "tonnes_live_weight",
                            "dataset": _DATASET,
                        },
                    })

                    if len(observations) >= limit:
                        break
                if len(observations) >= limit:
                    break
            if len(observations) >= limit:
                break

        logger.info("EUMOFA returned %d fisheries records via Eurostat", len(observations))
        return observations
