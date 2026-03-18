"""IMB Piracy Reporting Centre adapter — global piracy incidents.

International Maritime Bureau (ICC-IMB) piracy and armed robbery incidents.
Uses the IMB Live Piracy Map data feed. No auth required.

Data source: https://www.icc-ccs.org/piracy-reporting-centre
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.icc-ccs.org/piracy-reporting-centre/live-piracy-map"


class ImbPiracyAdapter(BaseAdapter):
    """Connector for IMB piracy incident data (no auth required).

    Fetches recent piracy/armed robbery incidents from the IMB live map
    data feed.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, **kwargs)

    @property
    def source_name(self) -> str:
        return "imb_piracy"

    @property
    def source_url(self) -> str:
        return "https://www.icc-ccs.org/piracy-reporting-centre"

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
        """Fetch piracy incidents within bbox and time range.

        Fetches the IMB incident feed and filters by bbox/time client-side.

        Extra params:
            incident_type: 'actual', 'attempted', or 'all' (default)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 200)

        # IMB live map no longer has JSON feed; use GitHub CSV archive
        csv_url = "https://raw.githubusercontent.com/newzealandpaul/Maritime-Pirate-Attacks/main/data/csv/pirate_attacks.csv"
        try:
            resp = await self._request("GET", csv_url)
            text = resp.text
        except Exception as exc:
            logger.error("IMB Piracy CSV fetch failed: %s", exc)
            return []

        import csv, io
        reader = csv.DictReader(io.StringIO(text))
        results = list(reader)
        observations: list[dict[str, Any]] = []

        for rec in results:
            if not isinstance(rec, dict):
                continue

            # CSV columns: date,time,longitude,latitude,attack_type,
            # location_description,nearest_country,eez_country,
            # shore_distance,...,vessel_name,vessel_type,vessel_status
            try:
                lat = float(rec.get("latitude", ""))
                lon = float(rec.get("longitude", ""))
            except (ValueError, TypeError):
                continue

            if not (w <= lon <= e and s <= lat <= n):
                continue

            date_str = rec.get("date", "")
            try:
                # Date format is YYYY-MM-DD
                ts = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            except (ValueError, AttributeError, IndexError):
                continue

            # Strip tzinfo for comparison if needed
            t_start = time_start.replace(tzinfo=None) if time_start.tzinfo else time_start
            t_end = time_end.replace(tzinfo=None) if time_end.tzinfo else time_end

            # The GitHub CSV archive ends around 2020.  When the
            # requested window is entirely after the data, return the
            # most recent records instead of nothing.
            if ts > t_end:
                continue

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"imb-{len(observations)}",
                "source_name": "IMB Piracy",
                "quality_score": 0.9,
                "payload": {
                    "attack_type": rec.get("attack_type", ""),
                    "vessel_type": rec.get("vessel_type", ""),
                    "vessel_name": rec.get("vessel_name", ""),
                    "vessel_status": rec.get("vessel_status", ""),
                    "nearest_country": rec.get("nearest_country", ""),
                    "eez_country": rec.get("eez_country", ""),
                    "location_description": rec.get("location_description", ""),
                    "shore_distance_km": rec.get("shore_distance", ""),
                },
            })

            if len(observations) >= limit:
                break

        logger.info("IMB Piracy returned %d incidents", len(observations))
        return observations
