"""SeaLifeBase adapter — marine invertebrate species traits and data.

Sister database to FishBase covering marine invertebrates including
molluscs, crustaceans, echinoderms, and other non-fish marine species.
No auth required.

Data source: HuggingFace (cboettig/sealifebase) species parquet table.
The legacy REST API at fishbase.ropensci.org is no longer available.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Direct parquet URL for the species table on HuggingFace
SPECIES_PARQUET_URL = (
    "https://huggingface.co/datasets/cboettig/fishbase/resolve/main"
    "/data/slb/v25.04/parquet/species.parquet"
)


class SeaLifeBaseAdapter(BaseAdapter):
    """Connector for SeaLifeBase via HuggingFace parquet files (no auth required).

    Downloads the species parquet table and returns species metadata.
    Not a spatial observation source -- returns species trait data.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "sealifebase"

    @property
    def source_url(self) -> str:
        return "https://www.sealifebase.org/"

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
        """Fetch marine invertebrate species data from SeaLifeBase parquet on HuggingFace.

        Extra params:
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)

        try:
            import pyarrow.parquet as pq
        except ImportError:
            logger.error("pyarrow not installed: pip install pyarrow")
            return []

        try:
            resp = await self._request("GET", SPECIES_PARQUET_URL)
            table = pq.read_table(io.BytesIO(resp.content))
        except Exception as exc:
            logger.error("SeaLifeBase parquet fetch failed: %s", exc)
            return []

        df = table.to_pandas()
        if len(df) > limit:
            df = df.head(limit)

        w, s, e, n = bbox
        lon = (w + e) / 2
        lat = (s + n) / 2

        observations: list[dict[str, Any]] = []
        for _, rec in df.iterrows():
            spec_code = rec.get("SpecCode", "")
            genus = str(rec.get("Genus", "") or "")
            species = str(rec.get("Species", "") or "")
            sci_name = f"{genus} {species}".strip()

            observations.append({
                "obs_type": "biological",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"sealifebase-{spec_code}",
                "source_name": "SeaLifeBase",
                "quality_score": 0.9,
                "payload": {
                    "scientific_name": sci_name,
                    "genus": genus,
                    "species": species,
                    "family": str(rec.get("Family", "") or ""),
                    "order": str(rec.get("Order", "") or ""),
                    "class": str(rec.get("Class", "") or ""),
                    "common_name": str(rec.get("FBname", "") or ""),
                    "max_length_cm": rec.get("Length"),
                    "max_weight_kg": rec.get("Weight"),
                    "depth_range_shallow": rec.get("DepthRangeShallow"),
                    "depth_range_deep": rec.get("DepthRangeDeep"),
                    "importance": str(rec.get("Importance", "") or ""),
                    "dangerous": str(rec.get("Dangerous", "") or ""),
                },
            })

        logger.info("SeaLifeBase returned %d species", len(observations))
        return observations
