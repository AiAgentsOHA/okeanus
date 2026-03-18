"""FathomNet adapter -- deep-sea annotated image data.

FathomNet is an open-source image database for ocean exploration, containing
annotated underwater images with species identifications and bounding boxes.
The REST API provides access to images, annotations, and taxa. No auth
required for read access.

Source: https://fathomnet.org/
API:    https://database.fathomnet.org/api
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

API_BASE = "https://database.fathomnet.org/api"


class FathomNetAdapter(BaseAdapter):
    """Connector for FathomNet deep-sea image annotations (no auth).

    Uses the paginated REST API at database.fathomnet.org.
    Images are filtered client-side by bounding box.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=45.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fathomnet"

    @property
    def source_url(self) -> str:
        return "https://fathomnet.org/"

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
        """Fetch deep-sea image annotations from FathomNet.

        Extra params:
            limit: Max records to return (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)

        # Fetch a larger page from the paginated images endpoint,
        # then filter client-side by bbox.
        # Request more than limit since many may fall outside bbox.
        fetch_size = min(limit * 3, 500)

        url = f"{API_BASE}/images"
        api_params: dict[str, Any] = {
            "size": fetch_size,
            "sort": "timestamp,desc",
        }

        try:
            resp = await self._request("GET", url, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("FathomNet image fetch failed: %s", exc)
            return []

        # New API returns paginated Spring Data REST format
        if isinstance(data, dict):
            records = data.get("content", [])
        elif isinstance(data, list):
            records = data
        else:
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if len(observations) >= limit:
                break
            if not isinstance(rec, dict):
                continue

            lat = rec.get("latitude")
            lon = rec.get("longitude")
            if lat is None or lon is None:
                continue

            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue

            # Filter by bounding box
            if not (s <= lat <= n and w <= lon <= e):
                continue

            ts_str = rec.get("timestamp", rec.get("createdTimestamp", ""))
            try:
                if ts_str:
                    ts = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
                else:
                    ts = time_start
            except (ValueError, AttributeError):
                ts = time_start

            observations.append({
                "obs_type": "deep_sea_image",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"fathomnet-{rec.get("uuid", len(observations))}",
                "source_name": "FathomNet",
                "quality_score": 0.85,
                "payload": {
                    "image_url": rec.get("url", ""),
                    "depth_m": rec.get("depthMeters"),
                    "imaging_type": rec.get("imagingType", ""),
                    "contributors": rec.get("contributorsEmail", ""),
                    "temperature_c": rec.get("temperatureCelsius"),
                    "salinity": rec.get("salinity"),
                    "oxygen_ml_l": rec.get("oxygenMlL"),
                    "num_annotations": len(rec.get("boundingBoxes", [])),
                },
            })

        logger.info("FathomNet returned %d image records", len(observations))
        return observations
