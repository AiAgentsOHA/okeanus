"""FAO FishStatJ adapter — global fisheries production and value.

Global capture production and aquaculture production by species,
country, and fishing area since 1950. The authoritative dataset
for world fisheries economics.

API: REST/SDMX + bulk download.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.fao.org/fishery/static/Data"

# Key FishStatJ dataset identifiers
DATASETS = {
    "capture": "Global Capture Production",
    "aquaculture": "Global Aquaculture Production (Quantity)",
    "aquaculture_value": "Global Aquaculture Production (Value)",
    "commodities": "Fishery Commodities and Trade",
    "fleet": "Global Fishing Fleet",
    "employment": "Fisheries and Aquaculture Employment",
}


class FaoFishstatAdapter(BaseAdapter):
    """Connector for FAO FishStatJ — global fisheries economics (no auth).

    Returns global capture/aquaculture production, trade, fleet size,
    and employment data for 200+ countries since 1950.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fao_fishstat"

    @property
    def source_url(self) -> str:
        return "https://www.fao.org/fishery/en/statistics"

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
        """Fetch FAO FishStatJ data.

        Extra params:
            dataset: 'capture' (default), 'aquaculture', 'aquaculture_value', 'commodities', 'fleet', 'employment'
            country: ISO3 country code (e.g. 'CHN', 'NOR')
            species: species ASFIS code or common name
            area: FAO fishing area code (e.g. '27' = NE Atlantic)
            limit: max records (default: 500)
        """
        dataset = params.get("dataset", "capture")
        country = params.get("country")
        species = params.get("species")
        area = params.get("area")
        limit = params.get("limit", 500)

        year_start = time_start.year
        year_end = time_end.year

        # Try REST endpoint
        url = f"{BASE_URL}/{dataset}"
        query: dict[str, Any] = {
            "startYear": year_start,
            "endYear": year_end,
            "format": "json",
            "limit": limit,
        }
        if country:
            query["country"] = country
        if species:
            query["species"] = species
        if area:
            query["area"] = area

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.warning("FAO FishStatJ REST failed: %s, trying SDG API", exc)
            return await self._fetch_sdg_fisheries(country, year_start, year_end, limit)

        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("Year") or rec.get("year") or rec.get("PERIOD")
            value = rec.get("Value") or rec.get("value") or rec.get("QUANTITY")

            if value is None:
                continue

            try:
                yr = int(year)
                ts = datetime(yr, 1, 1)
                val = float(value)
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            ctry = rec.get("Country") or rec.get("country") or rec.get("COUNTRY", "")
            spec = rec.get("Species") or rec.get("species") or rec.get("ASFIS_species", "")

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"fishstat-{dataset}-{ctry}-{spec}-{yr}",
                "source_name": "FAO FishStatJ",
                "quality_score": 0.95,
                "payload": {
                    "dataset": dataset,
                    "dataset_name": DATASETS.get(dataset, dataset),
                    "country": ctry,
                    "species": spec,
                    "scientific_name": rec.get("Scientific_Name") or rec.get("scientific_name", ""),
                    "fishing_area": rec.get("Fishing_Area") or rec.get("area", area or ""),
                    "year": yr,
                    "value": val,
                    "unit": rec.get("Unit") or rec.get("unit", "tonnes"),
                    "status": rec.get("Status") or rec.get("status", ""),
                },
            })

        logger.info("FAO FishStatJ %s returned %d records", dataset, len(observations))
        return observations

    async def _fetch_sdg_fisheries(
        self,
        country: str | None,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: fetch SDG 14 fisheries indicators."""
        url = "https://unstats.un.org/SDGAPI/v1/sdg/Indicator/Data"
        query = {
            "indicator": "14.4.1",  # Proportion of fish stocks within biologically sustainable levels
            "timePeriod": f"{year_start}-{year_end}",
            "pageSize": limit,
        }
        if country:
            query["areaCode"] = country

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("SDG fisheries fallback failed: %s", exc)
            return []

        records = data.get("data", [])
        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            year = rec.get("timePeriodStart") or rec.get("year")
            value = rec.get("value")
            if value is None:
                continue

            try:
                yr = int(year)
                ts = datetime(yr, 1, 1)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"sdg-14.4.1-{rec.get('geoAreaCode','')}-{yr}",
                "source_name": "FAO/SDG",
                "quality_score": 0.90,
                "payload": {
                    "indicator": "SDG 14.4.1",
                    "indicator_name": "Fish stocks within sustainable levels (%)",
                    "country": rec.get("geoAreaName", ""),
                    "country_code": rec.get("geoAreaCode", ""),
                    "year": yr,
                    "value": float(value),
                    "unit": "%",
                },
            })

        return observations
