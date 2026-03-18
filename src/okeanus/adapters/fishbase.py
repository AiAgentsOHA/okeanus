"""FishBase adapter -- fish species traits and distribution data.

35K+ fish species with ecology, morphology, distribution, and trait data.
No auth required.

Data source: HuggingFace (cboettig/fishbase) species parquet table.
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
    "/data/fb/v25.04/parquet/species.parquet"
)


class FishBaseAdapter(BaseAdapter):
    """Connector for FishBase via HuggingFace parquet files (no auth required).

    Downloads the species parquet table and returns species metadata.
    Not a spatial observation source -- returns species trait data.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fishbase"

    @property
    def source_url(self) -> str:
        return "https://www.fishbase.org/"

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
        """Fetch fish species data from FishBase parquet on HuggingFace.

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
            logger.error("FishBase parquet fetch failed: %s", exc)
            return []

        df = table.to_pandas()
        # Take a sample up to limit
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
                "source_id": f"fishbase-{spec_code}",
                "source_name": "FishBase",
                "quality_score": 0.9,
                "payload": {
                    "scientific_name": sci_name,
                    "genus": genus,
                    "species": species,
                    "common_name": str(rec.get("FBname", "") or ""),
                    "spec_code": int(spec_code) if spec_code else None,
                    "body_shape": str(rec.get("BodyShapeI", "") or ""),
                    "vulnerability": rec.get("Vulnerability"),
                    "importance": str(rec.get("Importance", "") or ""),
                    "depth_range_shallow": rec.get("DepthRangeShallow"),
                    "depth_range_deep": rec.get("DepthRangeDeep"),
                    "dangerous": str(rec.get("Dangerous", "") or ""),
                    "freshwater": bool(rec.get("Fresh")),
                    "saltwater": bool(rec.get("Saltwater")),
                },
            })

        logger.info("FishBase returned %d species", len(observations))
        return observations
