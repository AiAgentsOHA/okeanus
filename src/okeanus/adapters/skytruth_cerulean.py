"""SkyTruth Cerulean adapter — satellite-detected oil slicks, near-real-time.

Cerulean uses Sentinel-1 SAR imagery to detect potential oil pollution
events globally. Data is served via an OGC-compliant REST API. No auth.

Source: https://cerulean.skytruth.org/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.cerulean.skytruth.org/collections/public.slick_plus/items"


class SkytruthCeruleanAdapter(BaseAdapter):
    """Connector for SkyTruth Cerulean oil slick detections."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "skytruth_cerulean"

    @property
    def source_url(self) -> str:
        return "https://cerulean.skytruth.org/"

    @property
    def update_frequency(self) -> str:
        return "near-real-time"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch detected oil slicks within bbox and time window.

        Extra params:
            limit: Max records (default 50)
            min_confidence: Minimum confidence score (0-1)
        """
        limit = params.get("limit", 50)
        w, s, e, n = bbox

        start_str = time_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = time_end.strftime("%Y-%m-%dT%H:%M:%SZ")

        query_params: dict[str, Any] = {
            "bbox": f"{w},{s},{e},{n}",
            "datetime": f"{start_str}/{end_str}",
            "limit": limit,
        }

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("SkyTruth Cerulean fetch failed: %s", exc)
            return []

        features = []
        if isinstance(data, dict):
            features = data.get("features", data.get("results", []))
        elif isinstance(data, list):
            features = data

        observations: list[dict[str, Any]] = []
        for feat in features:
            if len(observations) >= limit:
                break

            props = feat.get("properties", feat)
            geom = feat.get("geometry")

            date_str = props.get("slick_timestamp", props.get("timestamp", props.get("date", props.get("created_at", ""))))
            ts = _parse_date(date_str)
            if ts is None:
                ts = datetime.now(timezone.utc)

            # Ensure tz-aware comparison
            _start = time_start if time_start.tzinfo else time_start.replace(tzinfo=timezone.utc)
            _end = time_end if time_end.tzinfo else time_end.replace(tzinfo=timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < _start or ts > _end:
                continue

            area_km2 = props.get("area_km2", props.get("area"))
            confidence = props.get("machine_confidence", props.get("confidence", props.get("ml_confidence")))
            slick_id = props.get("id", props.get("slick_id", ""))

            observations.append({
                "obs_type": "oil_slick",
                "timestamp": ts,
                "geometry": geom,
                "source_id": f"cerulean-{slick_id}",
                "source_name": "SkyTruth Cerulean",
                "quality_score": float(confidence) if confidence else None,
                "payload": {
                    "slick_id": slick_id,
                    "area_km2": area_km2,
                    "confidence": confidence,
                    "source_type": props.get("source_type", props.get("infrastructure_type", "")),
                    "vessel_mmsi": props.get("mmsi"),
                    "vessel_name": props.get("vessel_name", ""),
                    "scene_id": props.get("scene_id", ""),
                },
            })

        logger.info("SkyTruth Cerulean returned %d oil slick detections", len(observations))
        return observations


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
