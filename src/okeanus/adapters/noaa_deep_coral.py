"""NOAA Deep-Sea Coral and Sponge Database adapter.

Over 700,000 records of deep-sea coral and sponge observations from NOAA's
National Centers for Environmental Information (NCEI). No auth required.

Data source: https://www.ncei.noaa.gov/products/deep-sea-coral-data
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ERDDAP_URL = "https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals.json"


class NoaaDeepCoralAdapter(BaseAdapter):
    """Connector for NOAA Deep-Sea Coral & Sponge Database via ERDDAP (no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_deep_coral"

    @property
    def source_url(self) -> str:
        return "https://www.ncei.noaa.gov/products/deep-sea-coral-data"

    @property
    def update_frequency(self) -> str:
        return "quarterly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch deep-sea coral and sponge observations within bbox.

        Extra params:
            phylum: filter by phylum (e.g. 'Cnidaria', 'Porifera')
            min_depth: minimum depth in meters
            max_depth: maximum depth in meters
            limit: max records to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        phylum = params.get("phylum")
        min_depth = params.get("min_depth")
        max_depth = params.get("max_depth")

        # Build ERDDAP constraint query string
        constraints: list[str] = [
            f"latitude>={s}",
            f"latitude<={n}",
            f"longitude>={w}",
            f"longitude<={e}",
        ]
        if phylum:
            constraints.append(f'Phylum="{phylum}"')
        if min_depth is not None:
            constraints.append(f"DepthInMeters>={min_depth}")
        if max_depth is not None:
            constraints.append(f"DepthInMeters<={max_depth}")

        constraint_str = "&".join(constraints)
        fields = (
            "latitude,longitude,ScientificName,VernacularNameCategory,"
            "Phylum,Class,Order,Family,Genus,Species,"
            "DepthInMeters,Temperature,Substrate,SamplingEquipment,"
            "ObservationDate,ObservationYear,CatalogNumber,Repository"
        )
        url = f"{ERDDAP_URL}?{fields}&{constraint_str}&orderByLimit(\"{limit}\")"

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA Deep Coral fetch failed: %s", exc)
            return []

        table = data.get("table", {})
        col_names = table.get("columnNames", [])
        rows = table.get("rows", [])

        observations: list[dict[str, Any]] = []
        for row in rows:
            rec = dict(zip(col_names, row))
            lat = rec.get("latitude")
            lon = rec.get("longitude")
            if lat is None or lon is None:
                continue

            raw_date = rec.get("ObservationDate") or rec.get("ObservationYear")
            try:
                if isinstance(raw_date, str) and "T" in raw_date:
                    ts = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                elif raw_date and str(raw_date).replace(".", "").isdigit():
                    ts = datetime(int(float(raw_date)), 1, 1)
                else:
                    ts = datetime(1900, 1, 1)
            except (ValueError, TypeError, OSError):
                ts = datetime(1900, 1, 1)

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"noaa-coral-{rec.get('CatalogNumber', len(observations))}",
                "source_name": "NOAA Deep-Sea Coral",
                "quality_score": 0.85,
                "payload": {
                    "scientific_name": rec.get("ScientificName", ""),
                    "common_name": rec.get("VernacularNameCategory", ""),
                    "phylum": rec.get("Phylum", ""),
                    "class": rec.get("Class", ""),
                    "order": rec.get("Order", ""),
                    "family": rec.get("Family", ""),
                    "genus": rec.get("Genus", ""),
                    "species": rec.get("Species", ""),
                    "depth_m": rec.get("DepthInMeters"),
                    "temperature": rec.get("Temperature"),
                    "substrate": rec.get("Substrate", ""),
                    "sample_method": rec.get("SamplingEquipment", ""),
                    "collection_date": rec.get("ObservationDate"),
                    "repository": rec.get("Repository", ""),
                },
            })

        logger.info("NOAA Deep Coral returned %d features", len(observations))
        return observations
