"""ESVD (Ecosystem Services Valuation Database) adapter.

Economic values ($/ha/year) for marine and coastal ecosystem services
including mangroves, coral reefs, seagrass, estuaries, open ocean.

Data: Database at esvd.info.
Free registration required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://esvd.info/api/v1"

# Marine/coastal ecosystem types
MARINE_BIOMES = {
    "coral_reef": "Coral reefs",
    "mangrove": "Mangroves",
    "seagrass": "Seagrass/algae beds",
    "estuary": "Estuaries",
    "coastal_wetland": "Coastal wetlands",
    "salt_marsh": "Salt marshes",
    "open_ocean": "Open ocean",
    "continental_shelf": "Continental shelf",
    "deep_sea": "Deep sea",
    "coastal_systems": "Coastal systems (general)",
}

# Key ecosystem service categories
SERVICE_TYPES = {
    "provisioning": "Food, raw materials, genetic resources",
    "regulating": "Climate regulation, carbon sequestration, coastal protection",
    "habitat": "Nursery, biodiversity maintenance",
    "cultural": "Recreation, tourism, aesthetic",
}


class EsvdAdapter(BaseAdapter):
    """Connector for ESVD — ecosystem services $/ha values (free reg).

    Returns economic valuations of marine and coastal ecosystem services
    from peer-reviewed studies worldwide.
    """

    def __init__(self, *, api_key: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._api_key = api_key

    @property
    def source_name(self) -> str:
        return "esvd"

    @property
    def source_url(self) -> str:
        return "https://esvd.info/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch ESVD ecosystem valuation data.

        Extra params:
            biome: ecosystem type (default: all marine)
            service_type: 'provisioning', 'regulating', 'habitat', 'cultural'
            country: country name
            limit: max records (default: 500)
        """
        biome = params.get("biome")
        service_type = params.get("service_type")
        country = params.get("country")
        limit = params.get("limit", 500)

        url = f"{BASE_URL}/values"
        query: dict[str, Any] = {
            "biome_type": "marine",
            "limit": limit,
            "format": "json",
        }
        if biome:
            query["biome"] = biome
        if service_type:
            query["service_type"] = service_type
        if country:
            query["country"] = country

        try:
            resp = await self._request(
                "GET", url, params=query, headers=self._headers(),
            )
            data = resp.json()
        except Exception as exc:
            logger.error("ESVD fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("values", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            study_year = rec.get("year") or rec.get("studyYear") or rec.get("valuation_year")
            value = rec.get("value") or rec.get("unitValue") or rec.get("value_per_ha")

            if value is None:
                continue

            try:
                yr = int(study_year) if study_year else time_end.year
                ts = datetime(yr, 1, 1)
                val = float(value)
            except (ValueError, TypeError):
                continue

            lat = rec.get("latitude") or rec.get("lat") or 0
            lon = rec.get("longitude") or rec.get("lon") or 0

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)],
                },
                "source_id": f"esvd-{rec.get('id', len(observations))}",
                "source_name": "ESVD",
                "quality_score": 0.85,
                "payload": {
                    "biome": rec.get("biome") or rec.get("ecosystem_type", ""),
                    "biome_name": MARINE_BIOMES.get(
                        rec.get("biome", ""), rec.get("biome_name", ""),
                    ),
                    "service_type": rec.get("serviceType") or rec.get("service_category", ""),
                    "service_name": rec.get("serviceName") or rec.get("service", ""),
                    "value_per_ha_year": val,
                    "currency": rec.get("currency", "USD"),
                    "valuation_method": rec.get("method") or rec.get("valuation_method", ""),
                    "country": rec.get("country") or rec.get("Country", ""),
                    "study_year": yr,
                    "reference": rec.get("reference") or rec.get("citation", ""),
                    "confidence": rec.get("confidence") or rec.get("reliability", ""),
                },
            })

        logger.info("ESVD returned %d ecosystem valuations", len(observations))
        return observations
