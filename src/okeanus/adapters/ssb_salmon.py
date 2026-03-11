"""Norway SSB (Statistics Norway) salmon price adapter.

Weekly salmon export prices in NOK/kg and volumes — the global
benchmark for farmed Atlantic salmon pricing.

API: JSON-stat REST at data.ssb.no.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://data.ssb.no/api/v0/en/table"

# Key SSB tables for salmon/seafood
TABLES = {
    "03024": "Salmon: weekly export prices and volumes",
    "08801": "Aquaculture: production and value by species",
    "07326": "Export of fish by country and species (monthly)",
    "09288": "Fisheries: catch by species group",
}


class SsbSalmonAdapter(BaseAdapter):
    """Connector for Norway SSB — salmon prices/volumes (no auth required).

    Returns weekly salmon export prices (NOK/kg), production volumes,
    and trade data from the world's #1 farmed salmon producer.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ssb_salmon"

    @property
    def source_url(self) -> str:
        return "https://data.ssb.no/"

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
        """Fetch SSB salmon/seafood data.

        Extra params:
            table: SSB table number (default: '03024' = weekly salmon)
            species: filter by species name
        """
        table = params.get("table", "03024")

        # SSB uses POST with JSON-stat query
        url = f"{BASE_URL}/{table}"

        # Build query body
        year_start = time_start.year
        year_end = time_end.year
        years = [str(y) for y in range(year_start, year_end + 1)]

        body: dict[str, Any] = {
            "query": [
                {
                    "code": "Tid",
                    "selection": {
                        "filter": "item",
                        "values": years,
                    },
                },
            ],
            "response": {"format": "json-stat2"},
        }

        try:
            resp = await self._request("POST", url, json=body)
            data = resp.json()
        except Exception as exc:
            logger.error("SSB fetch table %s failed: %s", table, exc)
            return []

        observations: list[dict[str, Any]] = []

        # Parse JSON-stat2 format
        dataset = data if "dimension" in data else data.get("dataset", data)
        dims = dataset.get("dimension", {})
        values = dataset.get("value", [])
        sizes = dataset.get("size", [])
        ids = dataset.get("id", [])

        if not values or not dims:
            return []

        # Extract time dimension
        time_dim_name = None
        for dim_id in ids:
            if dim_id.lower() in ("tid", "time", "year", "week"):
                time_dim_name = dim_id
                break

        if not time_dim_name:
            time_dim_name = ids[-1] if ids else "Tid"

        time_cats = dims.get(time_dim_name, {}).get("category", {})
        time_labels = time_cats.get("label", {})
        time_indices = time_cats.get("index", {})

        # Map flat index to dimension values
        # For simplicity, iterate values with time dimension as last
        idx = 0
        other_dims = [d for d in ids if d != time_dim_name]

        # Get labels for other dimensions
        other_labels = {}
        for d in other_dims:
            cat = dims.get(d, {}).get("category", {})
            other_labels[d] = cat.get("label", {})

        # Compute strides for flat index
        total = len(values)
        time_size = len(time_labels) if time_labels else 1

        for i, val in enumerate(values):
            if val is None:
                continue

            # Calculate time index
            time_idx = i % time_size
            time_key = list(time_labels.keys())[time_idx] if time_idx < len(time_labels) else ""
            time_label = time_labels.get(time_key, time_key)

            # Parse time period
            try:
                if "W" in time_key or "w" in time_key:
                    # Weekly: 2024W01
                    yr = int(time_key[:4])
                    wk = int(time_key[-2:])
                    ts = datetime(yr, 1, 1) + __import__("datetime").timedelta(weeks=wk - 1)
                elif len(time_key) == 4:
                    ts = datetime(int(time_key), 1, 1)
                elif "M" in time_key:
                    parts = time_key.split("M")
                    ts = datetime(int(parts[0]), int(parts[1]), 1)
                else:
                    ts = datetime(int(time_key[:4]), 1, 1)
            except (ValueError, TypeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            # Build context from other dimensions
            context: dict[str, str] = {}
            remaining = i // time_size
            for d in reversed(other_dims):
                d_size = len(other_labels.get(d, {})) or 1
                d_idx = remaining % d_size
                remaining //= d_size
                d_keys = list(other_labels.get(d, {}).keys())
                if d_idx < len(d_keys):
                    context[d] = other_labels[d].get(d_keys[d_idx], d_keys[d_idx])

            # Norway centroid
            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [10.75, 59.91]},
                "source_id": f"ssb-{table}-{i}",
                "source_name": "SSB Norway",
                "quality_score": 0.97,
                "payload": {
                    "table": table,
                    "table_name": TABLES.get(table, f"SSB table {table}"),
                    "period": time_key,
                    "period_label": time_label,
                    "value": val,
                    **context,
                },
            })

        logger.info("SSB table %s returned %d observations", table, len(observations))
        return observations
