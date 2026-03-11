"""Copernicus Data Space adapter — Sentinel satellite data catalog.

The Copernicus Data Space Ecosystem provides STAC catalog access to
all Sentinel satellite data (S1 SAR, S2 optical, S3 ocean, S5P atmo,
S6 altimetry). Free registration required for download; catalog
browsing is open. No auth required for search.

Data source: https://dataspace.copernicus.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

STAC_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"


class CopernicusDataspaceAdapter(BaseAdapter):
    """Connector for Copernicus Data Space STAC catalog (no auth for search)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "copernicus_dataspace"

    @property
    def source_url(self) -> str:
        return "https://dataspace.copernicus.eu/"

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
        """Search Copernicus STAC catalog for satellite scenes.

        Extra params:
            collection: Sentinel collection (default 'SENTINEL-3')
                Options: SENTINEL-1, SENTINEL-2, SENTINEL-3, SENTINEL-5P, SENTINEL-6
            product_type: filter by product type (e.g. 'OL_2_WFR___' for ocean color)
            limit: max results (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        collection = params.get("collection", "SENTINEL-3")
        product_type = params.get("product_type")

        body: dict[str, Any] = {
            "bbox": [w, s, e, n],
            "datetime": f"{time_start.isoformat()}Z/{time_end.isoformat()}Z",
            "collections": [collection],
            "limit": min(limit, 200),
        }

        if product_type:
            body["filter"] = f"productType = '{product_type}'"

        try:
            resp = await self._request(
                "POST", STAC_URL, json=body,
                headers={"Content-Type": "application/json"},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("Copernicus Data Space fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features[:limit]:
            if not isinstance(feat, dict):
                continue

            props = feat.get("properties", {})
            geom = feat.get("geometry")

            # Use centroid of footprint
            if geom and geom.get("type") == "Polygon":
                coords = geom.get("coordinates", [[]])
                ring = coords[0] if coords else []
                if ring:
                    lon = sum(pt[0] for pt in ring) / len(ring)
                    lat = sum(pt[1] for pt in ring) / len(ring)
                else:
                    continue
            else:
                bbox_feat = feat.get("bbox", [w, s, e, n])
                lon = (bbox_feat[0] + bbox_feat[2]) / 2
                lat = (bbox_feat[1] + bbox_feat[3]) / 2

            dt_str = props.get("datetime", props.get("created", ""))
            try:
                ts = datetime.fromisoformat(dt_str.replace("Z", "+00:00")) if dt_str else time_start
            except (ValueError, AttributeError):
                ts = time_start

            observations.append({
                "obs_type": "satellite",
                "timestamp": ts,
                "geometry": geom or {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"cdse-{feat.get('id', '')}",
                "source_name": "Copernicus Data Space",
                "quality_score": 0.9,
                "payload": {
                    "collection": collection,
                    "product_type": props.get("productType", ""),
                    "title": props.get("title", ""),
                    "platform": props.get("platform", ""),
                    "instrument": props.get("instrument", ""),
                    "cloud_cover_pct": props.get("eo:cloud_cover"),
                    "orbit_number": props.get("sat:relative_orbit"),
                    "processing_level": props.get("processing:level", ""),
                    "download_link": feat.get("assets", {}).get("PRODUCT", {}).get("href", ""),
                },
            })

        logger.info("Copernicus Data Space returned %d scenes", len(observations))
        return observations
