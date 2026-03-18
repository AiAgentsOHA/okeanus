"""Sea Around Us (UBC) adapter — reconstructed catch + value by EEZ.

Reconstructed global marine catch data since 1950 with economic
valuation, by EEZ, species, fishing country, and sector.

Data: CSV download at seaaroundus.org.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.seaaroundus.org/api/v1"


class SeaAroundUsAdapter(BaseAdapter):
    """Connector for Sea Around Us — catch + value by EEZ (no auth).

    Returns reconstructed marine catch and landed value data from
    the University of British Columbia's Sea Around Us project.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "sea_around_us"

    @property
    def source_url(self) -> str:
        return "https://www.seaaroundus.org/"

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
        """Fetch Sea Around Us catch/value data.

        Extra params:
            region_type: 'eez' (default), 'lme', 'rfmo', 'highseas', 'fishing-entity'
            region_id: numeric region identifier
            dimension: 'taxon', 'commercialgroup', 'functionalgroup', 'country', 'sector'
            measure: 'tonnage' (default) or 'value'
            limit: max records (default: 500)
        """
        region_type = params.get("region_type", "eez")
        region_id = params.get("region_id", 356)  # Default: India (known valid EEZ)
        dimension = params.get("dimension", "taxon")
        measure = params.get("measure", "tonnage")
        limit = params.get("limit", 500)

        url = f"{BASE_URL}/{region_type}/{measure}/{dimension}/"
        query: dict[str, Any] = {
            "region_id": region_id,
            "format": "json",
        }

        try:
            resp = await self._request("GET", url, params=query)
            data = resp.json()
        except Exception as exc:
            logger.error("Sea Around Us fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("data", data.get("values", []))
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            entity_name = rec.get("key") or rec.get("name") or rec.get("entity_name", "")
            values = rec.get("values", [])

            if not isinstance(values, list):
                continue

            for val_entry in values:
                if not isinstance(val_entry, (list, tuple)) or len(val_entry) < 2:
                    continue

                year = val_entry[0]
                value = val_entry[1]

                try:
                    yr = int(year)
                    if yr > time_end.year:
                        continue
                    ts = datetime(yr, 1, 1)
                    val_f = float(value)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "economic",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "source_id": f"sau-{region_type}-{region_id}-{entity_name}-{yr}",
                    "source_name": "Sea Around Us",
                    "quality_score": 0.90,
                    "payload": {
                        "region_type": region_type,
                        "region_id": region_id,
                        "dimension": dimension,
                        "entity_name": entity_name,
                        "measure": measure,
                        "year": yr,
                        "value": val_f,
                        "unit": "tonnes" if measure == "tonnage" else "USD (2010 real)",
                    },
                })

                if len(observations) >= limit:
                    break

            if len(observations) >= limit:
                break

        logger.info("Sea Around Us returned %d observations", len(observations))
        return observations
