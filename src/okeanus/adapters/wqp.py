"""Water Quality Portal adapter — 430M+ water quality records.

The WQP is a cooperative service providing water quality data from EPA,
USGS, and USDA. Covers nutrients, contaminants, turbidity, dissolved
oxygen, and more. No auth required.

API docs: https://www.waterqualitydata.us/webservices_documentation/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

STATION_URL = "https://www.waterqualitydata.us/data/Station/search"


class WqpAdapter(BaseAdapter):
    """Connector for Water Quality Portal (EPA + USGS + USDA)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "wqp"

    @property
    def source_url(self) -> str:
        return "https://www.waterqualitydata.us/"

    @property
    def update_frequency(self) -> str:
        return "varies"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch water quality monitoring stations within bbox.

        Uses the Station endpoint (supports geojson) to get monitoring
        station locations with metadata.

        Extra params:
            characteristic: e.g. 'Dissolved oxygen', 'Nitrogen', 'pH'
            sample_media: 'Water' (default), 'Sediment'
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        w, s, e, n = bbox
        characteristic = params.get("characteristic", "")
        sample_media = params.get("sample_media", "Water")

        start_str = time_start.strftime("%m-%d-%Y")
        end_str = time_end.strftime("%m-%d-%Y")

        query_params: dict[str, Any] = {
            "bBox": f"{w},{s},{e},{n}",
            "startDateLo": start_str,
            "startDateHi": end_str,
            "sampleMedia": sample_media,
            "sorted": "no",
            "mimeType": "geojson",
            "zip": "no",
        }
        if characteristic:
            query_params["characteristicName"] = characteristic

        try:
            resp = await self._request("GET", STATION_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("WQP fetch failed: %s", exc)
            return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            if len(observations) >= limit:
                break

            props = feat.get("properties", {})
            geom = feat.get("geometry")

            # Use a generic timestamp since Station endpoint doesn't have per-result dates
            ts = datetime.now(timezone.utc)

            site_id = props.get("MonitoringLocationIdentifier", "")
            org = props.get("OrganizationFormalName", "")
            site_name = props.get("MonitoringLocationName", "")
            site_type = props.get("MonitoringLocationTypeName", "")
            huc = props.get("HUCEightDigitCode", "")

            observations.append({
                "obs_type": "water_quality",
                "timestamp": ts,
                "geometry": geom,
                "source_id": f"wqp-{site_id}",
                "source_name": "Water Quality Portal",
                "quality_score": 0.9,
                "payload": {
                    "site_id": site_id,
                    "site_name": site_name,
                    "site_type": site_type,
                    "organization": org,
                    "huc_code": huc,
                    "provider": props.get("ProviderName", ""),
                    "result_count": props.get("resultCount"),
                },
            })

        logger.info("WQP returned %d monitoring stations", len(observations))
        return observations


def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None
