"""iNaturalist adapter — citizen science biodiversity observations.

100M+ verifiable observations worldwide including marine species.
No auth required for basic searches (rate-limited to ~1 req/s).

API docs: https://api.inaturalist.org/v1/docs/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.inaturalist.org/v1"


class INaturalistAdapter(BaseAdapter):
    """Connector for iNaturalist observation search (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "inaturalist"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "real-time"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch observations within bbox and time range.

        Extra params:
            taxon_id: iNaturalist taxon ID (e.g. 47178 for Actinopterygii)
            quality_grade: 'research', 'needs_id', or 'casual'
            iconic_taxa: e.g. 'Actinopterygii', 'Mammalia', 'Mollusca'
        """
        w, s, e, n = bbox
        limit = min(params.get("limit", 200), 200)  # iNat max per_page=200

        api_params: dict[str, Any] = {
            "swlat": s,
            "swlng": w,
            "nelat": n,
            "nelng": e,
            "d1": time_start.strftime("%Y-%m-%d"),
            "d2": time_end.strftime("%Y-%m-%d"),
            "geo": "true",
            "per_page": limit,
            "order": "desc",
            "order_by": "observed_on",
            "quality_grade": params.get("quality_grade", "research"),
        }
        if taxon_id := params.get("taxon_id"):
            api_params["taxon_id"] = taxon_id
        if iconic_taxa := params.get("iconic_taxa"):
            api_params["iconic_taxa"] = iconic_taxa

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/observations", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("iNaturalist fetch failed: %s", exc)
            return []

        results = data.get("results", [])
        observations: list[dict[str, Any]] = []

        for rec in results:
            geojson = rec.get("geojson")
            if not geojson or geojson.get("type") != "Point":
                continue
            coords = geojson.get("coordinates", [])
            if len(coords) < 2:
                continue
            lon, lat = coords[0], coords[1]

            date_str = rec.get("observed_on_details", {}).get("date") or rec.get("observed_on", "")
            if not date_str:
                continue
            try:
                ts = datetime.fromisoformat(date_str + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            taxon = rec.get("taxon") or {}

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"inat-{rec.get('id', '')}",
                "source_name": "iNaturalist",
                "quality_score": 0.9 if rec.get("quality_grade") == "research" else 0.5,
                "payload": {
                    "scientific_name": taxon.get("name", ""),
                    "common_name": taxon.get("preferred_common_name", ""),
                    "taxon_id": taxon.get("id"),
                    "iconic_taxon": taxon.get("iconic_taxon_name", ""),
                    "rank": taxon.get("rank", ""),
                    "kingdom": taxon.get("ancestry_names", {}).get("kingdom", ""),
                    "quality_grade": rec.get("quality_grade", ""),
                    "num_identification_agreements": rec.get("num_identification_agreements", 0),
                    "photos": len(rec.get("photos", [])),
                    "user": rec.get("user", {}).get("login", ""),
                    "uri": rec.get("uri", ""),
                },
            })

        logger.info("iNaturalist returned %d observations", len(observations))
        return observations
