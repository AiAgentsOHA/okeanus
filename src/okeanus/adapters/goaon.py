"""GOA-ON adapter -- Global Ocean Acidification Observing Network.

GOA-ON coordinates ocean acidification observations from 1,000+ members
in 100+ countries. Provides station locations and metadata via their
Vizer-based portal. No auth required.

Data source: https://portal.goa-on.org/Explorer
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# GOA-ON portal uses a Vizer framework with PHP SSA (server-side API)
# endpoints. The get_siso_list.php endpoint returns all platform data
# including lat, lon, name, measurements, etc.
PORTAL_URL = "https://portal.goa-on.org/ssa/get_siso_list.php"


class GoaOnAdapter(BaseAdapter):
    """Connector for GOA-ON ocean acidification network (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "goaon"

    @property
    def source_url(self) -> str:
        return "https://www.goa-on.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch GOA-ON station locations and metadata within bbox.

        Extra params:
            platform_type: filter by platform (e.g. 'Fixed Ocean Time Series', 'Mooring')
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        platform_type = params.get("platform_type")

        # POST to the Vizer SSA endpoint with Explorer app context
        # The endpoint requires form-encoded 'app' parameter to authenticate
        try:
            resp = await self._request(
                "POST",
                PORTAL_URL,
                data="app=Explorer&use_grid_info=true",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("GOA-ON fetch failed: %s", exc)
            return []

        if not data.get("success"):
            logger.warning("GOA-ON returned success=false")
            return []

        items = data.get("items", [])
        if not isinstance(items, list):
            logger.warning("GOA-ON unexpected items format")
            return []

        observations: list[dict[str, Any]] = []

        for rec in items:
            if not isinstance(rec, dict):
                continue

            lat = rec.get("lat")
            lon = rec.get("lon")
            if lat is None or lon is None:
                continue

            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue

            # Filter by bbox
            if lat < s or lat > n or lon < w or lon > e:
                continue

            # Filter by platform type if specified
            ptype = rec.get("platform_type", "")
            if platform_type and platform_type.lower() not in ptype.lower():
                continue

            # Extract measurement names
            measurements = rec.get("measurements", [])
            var_names = []
            if isinstance(measurements, list):
                var_names = [m.get("name", "") for m in measurements if isinstance(m, dict)]

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"goaon-{rec.get('siso_label', '')}",
                "source_name": "GOA-ON",
                "quality_score": 0.85,
                "payload": {
                    "station_name": rec.get("name", rec.get("short_name", "")),
                    "platform_type": ptype,
                    "variables": var_names,
                    "region": rec.get("region", ""),
                    "provider": rec.get("provider", ""),
                    "deploy_status": rec.get("deploy_status", ""),
                    "info_url": rec.get("info_url", ""),
                },
            })

            if len(observations) >= limit:
                break

        logger.info("GOA-ON returned %d stations", len(observations))
        return observations
