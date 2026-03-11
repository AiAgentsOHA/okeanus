"""EUMOFA (European Market Observatory for Fisheries and Aquaculture) adapter.

108 species, first-sale to consumer prices across EU-27 + 4 countries.

Data: Bulk CSV download at eumofa.eu/bulk-download-page.
No auth required.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.eumofa.eu/webservices/rest/data"
BULK_URL = "https://www.eumofa.eu/api/v1"

# EUMOFA data categories
CATEGORIES = {
    "first_sale": "First-sale prices (ex-vessel)",
    "import": "Import prices",
    "export": "Export prices",
    "wholesale": "Wholesale prices",
    "consumer": "Consumer/retail prices",
    "production": "Production volumes",
}


class EumofaAdapter(BaseAdapter):
    """Connector for EUMOFA — EU fish prices 108 species (no auth required).

    Returns first-sale, wholesale, and retail prices for seafood species
    across European markets.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "eumofa"

    @property
    def source_url(self) -> str:
        return "https://www.eumofa.eu/"

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch EUMOFA seafood price/volume data.

        Extra params:
            category: data category (first_sale, import, export, etc.)
            species: species common name (e.g. 'salmon', 'cod')
            country: ISO2 country code (e.g. 'ES', 'NO')
            limit: max records (default: 500)
        """
        category = params.get("category", "first_sale")
        species = params.get("species")
        country = params.get("country")
        limit = params.get("limit", 500)

        year_start = time_start.year
        year_end = time_end.year

        # Try REST API first
        observations = await self._fetch_rest(
            category, species, country, year_start, year_end, limit,
        )

        if not observations:
            observations = await self._fetch_bulk_csv(
                category, species, country, year_start, year_end, limit,
            )

        logger.info("EUMOFA returned %d observations", len(observations))
        return observations

    async def _fetch_rest(
        self,
        category: str,
        species: str | None,
        country: str | None,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Try EUMOFA REST API endpoint."""
        url = f"{BASE_URL}/{category}"
        query: dict[str, Any] = {
            "startYear": year_start,
            "endYear": year_end,
            "format": "json",
        }
        if species:
            query["species"] = species
        if country:
            query["country"] = country

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception:
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(records, list):
            return []

        observations: list[dict[str, Any]] = []
        for rec in records[:limit]:
            if not isinstance(rec, dict):
                continue

            year = rec.get("year") or rec.get("Year")
            month = rec.get("month") or rec.get("Month") or 1
            price = rec.get("price") or rec.get("Price") or rec.get("value")

            if price is None:
                continue

            try:
                ts = datetime(int(year), int(month), 1)
                price_f = float(price)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [10.0, 50.0]},
                "source_id": f"eumofa-{category}-{rec.get('species','')}-{year}-{month}",
                "source_name": "EUMOFA",
                "quality_score": 0.93,
                "payload": {
                    "category": category,
                    "category_name": CATEGORIES.get(category, category),
                    "species": rec.get("species") or rec.get("Species", ""),
                    "country": rec.get("country") or rec.get("Country", ""),
                    "market": rec.get("market") or rec.get("Market", ""),
                    "price": price_f,
                    "currency": rec.get("currency", "EUR"),
                    "unit": rec.get("unit", "EUR/kg"),
                    "volume": rec.get("volume") or rec.get("Volume"),
                    "year": int(year),
                    "month": int(month),
                },
            })

        return observations

    async def _fetch_bulk_csv(
        self,
        category: str,
        species: str | None,
        country: str | None,
        year_start: int,
        year_end: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fallback: download bulk CSV from EUMOFA."""
        url = f"{BULK_URL}/download/{category}"
        query: dict[str, Any] = {"format": "csv"}

        try:
            resp = await self._request("GET", url, params=query)
            text = resp.text
        except Exception as exc:
            logger.error("EUMOFA CSV download failed: %s", exc)
            return []

        observations: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            year_val = row.get("Year") or row.get("year") or row.get("YEAR")
            if not year_val:
                continue

            try:
                yr = int(year_val)
                if yr < year_start or yr > year_end:
                    continue
            except ValueError:
                continue

            if species and species.lower() not in (row.get("Species", "") or "").lower():
                continue
            if country and country.upper() != (row.get("Country", "") or row.get("country_code", "")).upper():
                continue

            price_val = row.get("Price") or row.get("price") or row.get("Value") or row.get("value")
            if not price_val:
                continue

            try:
                price_f = float(price_val)
            except ValueError:
                continue

            month = int(row.get("Month") or row.get("month") or 1)

            observations.append({
                "obs_type": "economic",
                "timestamp": datetime(yr, month, 1),
                "geometry": {"type": "Point", "coordinates": [10.0, 50.0]},
                "source_id": f"eumofa-csv-{row.get('Species','')}-{yr}-{month}",
                "source_name": "EUMOFA",
                "quality_score": 0.90,
                "payload": {
                    "category": category,
                    "species": row.get("Species", ""),
                    "country": row.get("Country", ""),
                    "price": price_f,
                    "currency": row.get("Currency", "EUR"),
                    "volume": row.get("Volume"),
                    "year": yr,
                    "month": month,
                },
            })

            if len(observations) >= limit:
                break

        return observations
