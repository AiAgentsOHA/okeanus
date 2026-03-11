"""Movebank adapter — animal movement and tracking data.

Movebank is a free online platform for archiving, managing, and sharing
animal movement data collected via GPS, satellite, and radio telemetry.
Public studies accessible without auth; some studies require access request.

Data source: https://www.movebank.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.movebank.org/movebank/service/public/json"


class MovebankAdapter(BaseAdapter):
    """Connector for Movebank animal tracking (public studies, no auth)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "movebank"

    @property
    def source_url(self) -> str:
        return "https://www.movebank.org/"

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
        """Fetch animal tracking events from public Movebank studies.

        Extra params:
            study_id: specific Movebank study ID
            taxon: filter by taxon name (e.g. 'Chelonia mydas')
            sensor_type: filter by sensor (e.g. 'gps', 'argos')
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        study_id = params.get("study_id")
        taxon = params.get("taxon")

        if study_id:
            # Fetch events from a specific study
            url = f"{BASE_URL}?entity_type=event&study_id={study_id}"
            url += f"&timestamp_start={time_start.strftime('%Y%m%d%H%M%S')}000"
            url += f"&timestamp_end={time_end.strftime('%Y%m%d%H%M%S')}000"
            url += f"&bbox={s},{w},{n},{e}"
            url += f"&max_events_per_individual={limit}"
        else:
            # Search for public studies in the area
            url = f"{BASE_URL}?entity_type=study"
            url += f"&bbox={s},{w},{n},{e}"
            if taxon:
                url += f"&taxon_canonical_name={taxon}"

        try:
            resp = await self._request("GET", url)
            data = resp.json()
        except Exception as exc:
            logger.error("Movebank fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("individuals", data.get("studies", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            if study_id:
                # Event record
                lon = rec.get("location_long", rec.get("longitude"))
                lat = rec.get("location_lat", rec.get("latitude"))
                if lon is None or lat is None:
                    continue

                try:
                    lon, lat = float(lon), float(lat)
                except (ValueError, TypeError):
                    continue

                ts_raw = rec.get("timestamp")
                try:
                    ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00")) if ts_raw else time_start
                except (ValueError, AttributeError):
                    ts = time_start

                observations.append({
                    "obs_type": "biological",
                    "timestamp": ts,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"movebank-{rec.get('event_id', rec.get('id', ''))}",
                    "source_name": "Movebank",
                    "quality_score": 0.85,
                    "payload": {
                        "individual_id": rec.get("individual_id"),
                        "tag_id": rec.get("tag_id"),
                        "sensor_type": rec.get("sensor_type_id", ""),
                        "ground_speed": rec.get("ground_speed"),
                        "heading": rec.get("heading"),
                        "height_above_ellipsoid": rec.get("height_above_ellipsoid"),
                        "taxon": rec.get("individual_taxon_canonical_name", ""),
                    },
                })
            else:
                # Study record — represent as centroid
                lon = rec.get("main_location_long")
                lat = rec.get("main_location_lat")
                if lon is None or lat is None:
                    continue

                try:
                    lon, lat = float(lon), float(lat)
                except (ValueError, TypeError):
                    continue

                observations.append({
                    "obs_type": "biological",
                    "timestamp": time_start,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"movebank-study-{rec.get('id', '')}",
                    "source_name": "Movebank",
                    "quality_score": 0.8,
                    "payload": {
                        "study_name": rec.get("name", ""),
                        "study_id": rec.get("id"),
                        "taxon": rec.get("taxon_ids", ""),
                        "num_individuals": rec.get("number_of_individuals"),
                        "num_events": rec.get("number_of_events"),
                        "principal_investigator": rec.get("principal_investigator_name", ""),
                        "license_type": rec.get("license_type", ""),
                    },
                })

        logger.info("Movebank returned %d records", len(observations))
        return observations
