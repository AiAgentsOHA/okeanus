"""Tara Oceans adapter — global ocean microbiome and plankton data.

The Tara Oceans expedition (2009-2013) sampled ocean microbiomes
at 210 stations across all major ocean basins. Data includes
genomic, taxonomic, and environmental measurements.

Data served via the Tara Oceans Polar Circle companion site
and ENA/PANGAEA archives. Station metadata via open API.

Data source: https://oceans.taraexpeditions.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# PANGAEA Elasticsearch API for Tara Oceans datasets
PANGAEA_URL = "https://ws.pangaea.de/es/pangaea/panmd/_search"


class TaraOceansAdapter(BaseAdapter):
    """Connector for Tara Oceans expedition data (no auth required).

    Returns station metadata and dataset references from the
    Tara Oceans global microbiome survey via PANGAEA.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "tara_oceans"

    @property
    def source_url(self) -> str:
        return "https://oceans.taraexpeditions.org/"

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
        """Fetch Tara Oceans station/dataset metadata from PANGAEA.

        Extra params:
            query: search term within Tara Oceans (default 'Tara Oceans')
            limit: max records (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        query = params.get("query", "Tara Oceans")

        # Use PANGAEA Elasticsearch — no date filter for historical expeditions
        es_query: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": [
                        {"query_string": {"query": query}},
                    ],
                    "filter": [
                        {
                            "geo_bounding_box": {
                                "meanPosition": {
                                    "top_left": {"lat": n, "lon": w},
                                    "bottom_right": {"lat": s, "lon": e},
                                }
                            }
                        }
                    ],
                }
            },
            "size": min(limit, 100),
        }

        try:
            resp = await self._request(
                "POST", PANGAEA_URL,
                json=es_query,
                headers={"Content-Type": "application/json"},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("Tara Oceans / PANGAEA fetch failed: %s", exc)
            return []

        hits = data.get("hits", {}).get("hits", [])
        results = [h.get("_source", {}) for h in hits if isinstance(h, dict)]

        observations: list[dict[str, Any]] = []

        for rec in results:
            if len(observations) >= limit:
                break

            if not isinstance(rec, dict):
                continue

            # Extract location from meanPosition (PANGAEA geo_point field)
            mean_pos = rec.get("meanPosition")
            if not isinstance(mean_pos, dict) or "lat" not in mean_pos or "lon" not in mean_pos:
                continue

            try:
                lat_f = float(mean_pos["lat"])
                lon_f = float(mean_pos["lon"])
            except (ValueError, TypeError):
                continue

            title = rec.get("citation") or rec.get("title") or str(rec.get("URI", ""))
            doi = rec.get("URI") or rec.get("doi", "")
            date_str = rec.get("minDateTime") or rec.get("date", "")

            try:
                ts = datetime.fromisoformat(date_str[:10]) if date_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                "source_id": f"tara-{rec.get('id', rec.get('doi', len(observations)))}",
                "source_name": "Tara Oceans / PANGAEA",
                "quality_score": 0.95,
                "payload": {
                    "title": str(title)[:200],
                    "doi": str(doi),
                    "campaign": rec.get("campaign") or rec.get("expedition", "Tara Oceans"),
                    "parameters": rec.get("parameters", []),
                    "size": rec.get("size") or rec.get("dataPoints"),
                },
            })

        logger.info("Tara Oceans returned %d datasets", len(observations))
        return observations
