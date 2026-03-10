"""PANGAEA adapter — Earth & environmental science data repository.

400K+ datasets from research expeditions, moorings, lab measurements.
No auth required.

API docs: https://wiki.pangaea.de/wiki/API
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.pangaea.de"


class PangaeaAdapter(BaseAdapter):
    """Connector for PANGAEA dataset search API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "pangaea"

    @property
    def source_url(self) -> str:
        return BASE_URL

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

        api_params: dict[str, Any] = {
            "q": params.get("query", ""),
            "bbox": f"{w},{s},{e},{n}",
            "mindate": time_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "maxdate": time_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "count": limit,
            "offset": 0,
        }
        if topic := params.get("topic"):
            api_params["topic"] = topic

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/search", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("PANGAEA fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("results", [])
        observations: list[dict[str, Any]] = []

        for rec in results:
            # Extract spatial centroid from dataset extent
            geo = rec.get("geometry") or rec.get("spatialCoverage", {})
            if isinstance(geo, dict) and "coordinates" in geo:
                coords = geo["coordinates"]
                if geo.get("type") == "Point":
                    lon, lat = coords[0], coords[1]
                elif geo.get("type") == "Polygon" and coords:
                    # Use centroid of polygon
                    ring = coords[0] if coords else []
                    if ring:
                        lon = sum(c[0] for c in ring) / len(ring)
                        lat = sum(c[1] for c in ring) / len(ring)
                    else:
                        continue
                else:
                    continue
            elif "minLatitude" in rec:
                lat = (rec.get("minLatitude", 0) + rec.get("maxLatitude", 0)) / 2
                lon = (rec.get("minLongitude", 0) + rec.get("maxLongitude", 0)) / 2
            else:
                continue

            date_str = rec.get("minDateTime") or rec.get("citation", {}).get("year", "")
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                elif len(str(date_str)) == 4:
                    ts = datetime.fromisoformat(f"{date_str}-01-01T00:00:00+00:00")
                else:
                    ts = datetime.fromisoformat(str(date_str) + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            doi = rec.get("URI") or rec.get("doi", "")
            citation = rec.get("citation", "")
            if isinstance(citation, dict):
                citation = citation.get("citation", str(citation))

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"pangaea-{doi}",
                "source_name": "PANGAEA",
                "quality_score": 0.95,
                "payload": {
                    "doi": doi,
                    "citation": str(citation)[:500],
                    "title": rec.get("title", rec.get("citation", {}).get("title", "")),
                    "parameters": rec.get("parameters", []),
                    "size": rec.get("size"),
                    "type": rec.get("type", ""),
                    "topics": rec.get("topics", []),
                },
            })

        logger.info("PANGAEA returned %d datasets", len(observations))
        return observations
