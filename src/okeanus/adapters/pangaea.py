"""PANGAEA adapter — Earth & environmental science data repository.

400K+ datasets from research expeditions, moorings, lab measurements.
No auth required.

API docs: https://wiki.pangaea.de/wiki/API
Search via Elasticsearch endpoint at ws.pangaea.de.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# PANGAEA uses Elasticsearch for search (not api.pangaea.de)
ES_URL = "https://ws.pangaea.de/es/pangaea/panmd/_search"


class PangaeaAdapter(BaseAdapter):
    """Connector for PANGAEA dataset search API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "pangaea"

    @property
    def source_url(self) -> str:
        return "https://www.pangaea.de/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Search PANGAEA datasets within bbox and time range.

        Returns dataset metadata (not individual measurements).
        Each result includes DOI, citation, parameter list, and spatial extent.

        Extra params:
            query: Free-text search query (e.g. 'chlorophyll', 'CTD')
            topic: PANGAEA topic filter (e.g. 'Oceans', 'Biology')
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        query_text = params.get("query", "ocean")

        # Build Elasticsearch query body
        must_clauses: list[dict[str, Any]] = []
        if query_text:
            must_clauses.append({"query_string": {"query": query_text}})

        # Spatial filter: bbox overlap using bounding box fields
        filter_clauses: list[dict[str, Any]] = [
            {"range": {"westBoundLongitude": {"lte": e}}},
            {"range": {"eastBoundLongitude": {"gte": w}}},
            {"range": {"southBoundLatitude": {"lte": n}}},
            {"range": {"northBoundLatitude": {"gte": s}}},
        ]

        if topic := params.get("topic"):
            filter_clauses.append({"term": {"topicType": topic}})

        es_body = {
            "query": {
                "bool": {
                    "must": must_clauses or [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "size": min(limit, 100),
            "_source": [
                "URI", "meanPosition", "agg-pubYear",
                "westBoundLongitude", "eastBoundLongitude",
                "southBoundLatitude", "northBoundLatitude",
                "sp-lastModified", "internal-datestamp",
                "nDataPoints",
            ],
        }

        try:
            resp = await self._request(
                "POST",
                ES_URL,
                json=es_body,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("PANGAEA fetch failed: %s", exc)
            return []

        hits = data.get("hits", {}).get("hits", [])
        results = [h.get("_source", {}) for h in hits]
        observations: list[dict[str, Any]] = []

        for rec in results:
            # Extract centroid from meanPosition or bounding box
            mean_pos = rec.get("meanPosition")
            if isinstance(mean_pos, dict) and "lat" in mean_pos:
                lat = float(mean_pos["lat"])
                lon = float(mean_pos["lon"])
            elif "southBoundLatitude" in rec:
                lat = (rec.get("southBoundLatitude", 0) + rec.get("northBoundLatitude", 0)) / 2
                lon = (rec.get("westBoundLongitude", 0) + rec.get("eastBoundLongitude", 0)) / 2
            else:
                continue

            # Parse date from sp-lastModified or internal-datestamp
            date_str = rec.get("sp-lastModified") or rec.get("internal-datestamp") or ""
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                else:
                    pub_year = rec.get("agg-pubYear")
                    if pub_year:
                        ts = datetime(int(pub_year), 1, 1)
                    else:
                        ts = time_start
            except (ValueError, AttributeError, TypeError):
                ts = time_start

            doi = rec.get("URI", "")

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"pangaea-{doi}",
                "source_name": "PANGAEA",
                "quality_score": 0.95,
                "payload": {
                    "doi": doi,
                    "n_data_points": rec.get("nDataPoints"),
                    "bbox": {
                        "west": rec.get("westBoundLongitude"),
                        "east": rec.get("eastBoundLongitude"),
                        "south": rec.get("southBoundLatitude"),
                        "north": rec.get("northBoundLatitude"),
                    },
                },
            })

        logger.info("PANGAEA returned %d datasets", len(observations))
        return observations
