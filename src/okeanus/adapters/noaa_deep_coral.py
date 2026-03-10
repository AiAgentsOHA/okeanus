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

BASE_URL = "https://gis.ncei.noaa.gov/arcgis/rest/services/deep_sea_corals/MapServer/0/query"


class NoaaDeepCoralAdapter(BaseAdapter):
    """Connector for NOAA Deep-Sea Coral & Sponge Database via ArcGIS REST (no auth)."""

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

        clauses: list[str] = []
        if phylum:
            clauses.append(f"Phylum = '{phylum}'")
        if min_depth is not None:
            clauses.append(f"DepthInMeters >= {min_depth}")
        if max_depth is not None:
            clauses.append(f"DepthInMeters <= {max_depth}")
        where = " AND ".join(clauses) if clauses else "1=1"

        api_params: dict[str, Any] = {
            "where": where,
            "geometry": f"{w},{s},{e},{n}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "outSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "true",
            "resultRecordCount": limit,
            "f": "json",
        }

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("NOAA Deep Coral fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            geom = feat.get("geometry", {})
            attrs = feat.get("attributes", {})

            lon = geom.get("x")
            lat = geom.get("y")
            if lon is None or lat is None:
                continue

            raw_date = attrs.get("ObservationDate") or attrs.get("ObservationYear")
            try:
                if isinstance(raw_date, (int, float)) and raw_date > 1e10:
                    ts = datetime.utcfromtimestamp(raw_date / 1000)
                elif raw_date and str(raw_date).isdigit():
                    ts = datetime(int(raw_date), 1, 1)
                else:
                    ts = datetime(1900, 1, 1)
            except (ValueError, TypeError, OSError):
                ts = datetime(1900, 1, 1)

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"noaa-coral-{attrs.get('CatalogNumber', attrs.get('OBJECTID', ''))}",
                "source_name": "NOAA Deep-Sea Coral",
                "quality_score": 0.85,
                "payload": {
                    "scientific_name": attrs.get("ScientificName", ""),
                    "common_name": attrs.get("VernacularNameCategory", ""),
                    "phylum": attrs.get("Phylum", ""),
                    "class": attrs.get("Class", ""),
                    "order": attrs.get("Order", ""),
                    "family": attrs.get("Family", ""),
                    "genus": attrs.get("Genus", ""),
                    "species": attrs.get("Species", ""),
                    "depth_m": attrs.get("DepthInMeters"),
                    "temperature": attrs.get("Temperature"),
                    "substrate": attrs.get("Substrate", ""),
                    "sample_method": attrs.get("SamplingEquipment", ""),
                    "collection_date": attrs.get("ObservationDate"),
                    "repository": attrs.get("Repository", ""),
                },
            })

        logger.info("NOAA Deep Coral returned %d features", len(observations))
        return observations
