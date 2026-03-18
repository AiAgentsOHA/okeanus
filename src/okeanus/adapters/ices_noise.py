"""ICES Underwater Noise Registry adapter — impulsive noise events.

The ICES Impulsive Noise Registry collects data on underwater noise sources
(pile driving, seismic surveys, explosions, sonar) across OSPAR/HELCOM regions.
No auth required.

Source: https://underwaternoise.ices.dk/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

API_URL = "https://underwaternoise.ices.dk/impulsive/api/getNoiseBaseData"


class IcesNoiseAdapter(BaseAdapter):
    """Connector for ICES Underwater Noise Registry (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ices_noise"

    @property
    def source_url(self) -> str:
        return "https://underwaternoise.ices.dk/"

    @property
    def update_frequency(self) -> str:
        return "annual"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch underwater noise event records.

        Extra params:
            source_event: Filter by type ('Pile driving', 'Seismic', 'Explosion', 'Sonar')
            ospar_region: OSPAR region filter
            limit: Max records (default 200)
        """
        limit = params.get("limit", 200)
        source_event = params.get("source_event", "")
        ospar_region = params.get("ospar_region", "")
        w, s, e, n = bbox

        query_params: dict[str, Any] = {}

        # API supports year filter only (no bbox).
        # Data lags 2-3 years; start from most recent and work backwards.
        years = list(range(time_start.year, time_end.year + 1))
        # Also try up to 3 years before the window to handle lag
        for extra in range(1, 4):
            candidate = time_start.year - extra
            if candidate not in years:
                years.append(candidate)
        # Query most recent first so we return the freshest data
        years.sort(reverse=True)
        for year in years:
            query_params["year"] = year
            if source_event:
                query_params["SourceEvent"] = source_event
            if ospar_region:
                query_params["OSPARRegion"] = ospar_region

            try:
                resp = await self._request("GET", API_URL, params=query_params)
                data = resp.json()
            except Exception as exc:
                logger.warning("ICES noise fetch year %d failed: %s", year, exc)
                continue

            if not isinstance(data, list):
                data = data.get("data", data.get("results", []))

            observations: list[dict[str, Any]] = []

            for rec in data:
                if len(observations) >= limit:
                    break

                lat = rec.get("Latitude", rec.get("latitude"))
                lon = rec.get("Longitude", rec.get("longitude"))
                if lat is None or lon is None:
                    continue

                try:
                    lat, lon = float(lat), float(lon)
                except (ValueError, TypeError):
                    continue

                if not (w <= lon <= e and s <= lat <= n):
                    continue

                ts = datetime(year, 1, 1, tzinfo=timezone.utc)

                observations.append({
                    "obs_type": "noise",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"ices-noise-{rec.get('tblEventID', len(observations))}-{year}",
                    "source_name": "ICES Underwater Noise Registry",
                    "quality_score": 0.9,
                    "payload": {
                        "year": year,
                        "source_event": rec.get("source_Event", ""),
                        "ospar_region": rec.get("osparRegion", ""),
                        "helcom_sub_basin": rec.get("helcomSubBasin", ""),
                        "country": rec.get("country", ""),
                        "value": rec.get("value", ""),
                        "start_date": str(rec.get("start_date", "")).strip(),
                        "end_date": str(rec.get("end_date", "")).strip(),
                    },
                })

            if observations:
                logger.info("ICES noise returned %d records for %d", len(observations), year)
                return observations

        logger.info("ICES noise returned 0 records")
        return []
