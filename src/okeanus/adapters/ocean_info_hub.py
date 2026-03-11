"""Ocean Info Hub (OIH) adapter — IOC-UNESCO ocean knowledge graph.

The Ocean InfoHub (OIH) project aggregates metadata about ocean datasets,
experts, training resources, and institutions from distributed ocean data
providers via a unified SPARQL/REST interface. No auth required.

Data source: https://oceaninfohub.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.oceaninfohub.org/blazegraph/namespace/oih/sparql"


class OceanInfoHubAdapter(BaseAdapter):
    """Connector for IOC-UNESCO Ocean Info Hub (no auth required).

    Queries the OIH knowledge graph for spatially-relevant ocean datasets,
    experts, and institutions.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=30.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ocean_info_hub"

    @property
    def source_url(self) -> str:
        return "https://oceaninfohub.org/"

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
        """Search Ocean Info Hub for datasets related to an area.

        Extra params:
            search_type: 'dataset', 'expert', 'institution', 'training' (default 'dataset')
            keyword: text search keyword
            limit: max results (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        search_type = params.get("search_type", "dataset")
        keyword = params.get("keyword", "ocean")

        # Map search type to schema.org type
        type_map = {
            "dataset": "schema:Dataset",
            "expert": "schema:Person",
            "institution": "schema:Organization",
            "training": "schema:Course",
        }
        rdf_type = type_map.get(search_type, "schema:Dataset")

        sparql = f"""
PREFIX schema: <https://schema.org/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>

SELECT ?item ?name ?description ?url ?lat ?lon
WHERE {{
  ?item a {rdf_type} .
  ?item schema:name ?name .
  OPTIONAL {{ ?item schema:description ?description }}
  OPTIONAL {{ ?item schema:url ?url }}
  OPTIONAL {{
    ?item schema:spatialCoverage ?place .
    ?place schema:geo ?geo .
    ?geo schema:latitude ?lat .
    ?geo schema:longitude ?lon .
  }}
  FILTER(CONTAINS(LCASE(?name), LCASE("{keyword}")))
}}
LIMIT {limit}
"""

        try:
            resp = await self._request(
                "POST",
                BASE_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/sparql-results+json",
                },
                params={"query": sparql},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("Ocean Info Hub fetch failed: %s", exc)
            return []

        bindings = data.get("results", {}).get("bindings", [])
        observations: list[dict[str, Any]] = []

        for rec in bindings:
            lon_val = rec.get("lon", {}).get("value")
            lat_val = rec.get("lat", {}).get("value")

            if lon_val and lat_val:
                try:
                    lon, lat = float(lon_val), float(lat_val)
                except (ValueError, TypeError):
                    lon, lat = (w + e) / 2, (s + n) / 2
            else:
                # No spatial info — use bbox centroid
                lon, lat = (w + e) / 2, (s + n) / 2

            name = rec.get("name", {}).get("value", "")
            item_url = rec.get("item", {}).get("value", "")

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"oih-{item_url.split('/')[-1] if item_url else name[:20]}",
                "source_name": "Ocean Info Hub",
                "quality_score": 0.7,
                "payload": {
                    "name": name,
                    "description": rec.get("description", {}).get("value", ""),
                    "url": rec.get("url", {}).get("value", item_url),
                    "type": search_type,
                    "graph_uri": item_url,
                },
            })

        logger.info("Ocean Info Hub returned %d %s records", len(observations), search_type)
        return observations
