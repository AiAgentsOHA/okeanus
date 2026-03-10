"""BOLD (Barcode of Life Data System) adapter — DNA barcode records.

5M+ DNA barcode records linking specimens to species via genetic sequencing.
Marine eDNA reference library. No auth required.

API docs: https://v3.boldsystems.org/index.php/resources/api
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.boldsystems.org/index.php/API_Public"


class BoldAdapter(BaseAdapter):
    """Connector for BOLD Systems public API (no auth required).

    Returns DNA barcode specimen records with taxonomy, collection locality,
    and sequence metadata useful for eDNA reference matching.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "bold"

    @property
    def source_url(self) -> str:
        return "https://boldsystems.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch DNA barcode specimens with coordinates.

        BOLD API uses taxon-based queries. Spatial filtering is done
        client-side from the returned coordinates.

        Extra params:
            taxon: Taxon name (e.g. 'Chordata', 'Mollusca', 'Arthropoda')
            geo: Geographic region ('all' default, or 'marine')
        """
        w, s, e, n = bbox
        taxon = params.get("taxon", "Chordata")
        limit = params.get("limit", 200)

        # BOLD returns TSV by default; request JSON via combined endpoint
        api_params: dict[str, Any] = {
            "taxon": taxon,
            "geo": params.get("geo", "all"),
            "format": "json",
        }

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/combined", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("BOLD fetch failed: %s", exc)
            return []

        # BOLD returns {"bold_records": {"records": {id: {...}, ...}}}
        bold_records = data.get("bold_records", {}).get("records", {})
        if isinstance(bold_records, dict):
            records = list(bold_records.values())
        elif isinstance(bold_records, list):
            records = bold_records
        else:
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if not isinstance(rec, dict):
                continue

            specimen = rec.get("specimen_identifiers", {})
            taxonomy = rec.get("taxonomy", {})
            collection = rec.get("collection_event", {})
            sequences = rec.get("sequences", {})

            lat_str = collection.get("coordinates", {}).get("lat", "")
            lon_str = collection.get("coordinates", {}).get("lon", "")
            if not lat_str or not lon_str:
                continue

            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except (ValueError, TypeError):
                continue

            # Filter by bbox
            if not (w <= lon <= e and s <= lat <= n):
                continue

            # Filter by time
            date_str = collection.get("collectiondate", "")
            try:
                if date_str and len(date_str) >= 10:
                    ts = datetime.fromisoformat(date_str[:10] + "T00:00:00+00:00")
                elif date_str and len(date_str) == 4:
                    ts = datetime.fromisoformat(f"{date_str}-01-01T00:00:00+00:00")
                else:
                    continue
            except (ValueError, AttributeError):
                continue

            if ts < time_start or ts > time_end:
                continue

            phylum = taxonomy.get("phylum", {})
            species = taxonomy.get("species", {})

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"bold-{specimen.get('sampleid', specimen.get('processid', ''))}",
                "source_name": "BOLD",
                "quality_score": 0.9,
                "payload": {
                    "process_id": specimen.get("processid", ""),
                    "sample_id": specimen.get("sampleid", ""),
                    "scientific_name": species.get("taxon", {}).get("name", ""),
                    "phylum": phylum.get("taxon", {}).get("name", ""),
                    "class": taxonomy.get("class", {}).get("taxon", {}).get("name", ""),
                    "order": taxonomy.get("order", {}).get("taxon", {}).get("name", ""),
                    "family": taxonomy.get("family", {}).get("taxon", {}).get("name", ""),
                    "genus": taxonomy.get("genus", {}).get("taxon", {}).get("name", ""),
                    "bin_uri": rec.get("bin_uri", ""),
                    "marker_code": sequences.get("sequence", [{}])[0].get("markercode", "")
                    if isinstance(sequences.get("sequence"), list)
                    else "",
                    "sequence_length": sequences.get("sequence", [{}])[0].get("nucleotides", "")[:20]
                    if isinstance(sequences.get("sequence"), list)
                    else "",
                    "country": collection.get("country", ""),
                    "region": collection.get("region", ""),
                },
            })

            if len(observations) >= limit:
                break

        logger.info("BOLD returned %d barcode specimens", len(observations))
        return observations
