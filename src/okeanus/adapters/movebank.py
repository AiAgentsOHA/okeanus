"""Movebank adapter — animal movement and tracking data.

Movebank is a free online platform for archiving, managing, and sharing
animal movement data collected via GPS, satellite, and radio telemetry.
Public studies accessible without auth; some studies require access request.

Data source: https://www.movebank.org/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.movebank.org/movebank/service/public/json"


class MovebankAdapter(BaseAdapter):
    """Connector for Movebank animal tracking (public studies, no auth).

    Movebank's public/json endpoint is often slow or returns 429 when
    called after many other adapters in a test suite. This adapter uses
    a tight per-request timeout and two attempts with a brief pause
    between them to handle transient rate limits.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=25.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "movebank"

    @property
    def source_url(self) -> str:
        return "https://www.movebank.org/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def _movebank_get(
        self,
        query_params: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Issue a GET to Movebank with two attempts (handles 429 with a pause).

        Returns the parsed JSON list/dict, or None on failure.
        """
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    timeout=20.0, follow_redirects=True
                ) as client:
                    resp = await client.get(BASE_URL, params=query_params)
                    if resp.status_code == 429:
                        if attempt == 0:
                            logger.warning("Movebank 429 rate-limited, pausing 5s")
                            await asyncio.sleep(5)
                            continue
                        logger.error("Movebank 429 on second attempt, giving up")
                        return None
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                logger.warning("Movebank attempt %d failed: %s", attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(2)
                    continue
                return None
        return None

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
            limit: max records (default 50)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 50)
        study_id = params.get("study_id")
        taxon = params.get("taxon")

        # Clamp to reasonable region for global queries
        if (e - w) > 30 or (n - s) > 30:
            cx, cy = (w + e) / 2.0, (s + n) / 2.0
            w, s, e, n = cx - 10, cy - 10, cx + 10, cy + 10

        if study_id:
            query_params: dict[str, Any] = {
                "entity_type": "event",
                "study_id": study_id,
                "timestamp_start": f"{time_start.strftime('%Y%m%d%H%M%S')}000",
                "timestamp_end": f"{time_end.strftime('%Y%m%d%H%M%S')}000",
                "max_events_per_individual": limit,
            }
        else:
            query_params = {
                "entity_type": "study",
                "i_can_see_data": "true",
                "there_are_data_which_i_cannot_download": "false",
            }
            if taxon:
                query_params["taxon_canonical_name"] = taxon

        data = await self._movebank_get(query_params)
        if data is None:
            logger.error("Movebank fetch returned no data")
            return []

        results = data if isinstance(data, list) else data.get("individuals", data.get("studies", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []
        cx, cy = (w + e) / 2.0, (s + n) / 2.0

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            if study_id:
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
                lon = rec.get("main_location_long")
                lat = rec.get("main_location_lat")
                has_coords = lon is not None and lat is not None
                if has_coords:
                    try:
                        lon, lat = float(lon), float(lat)
                    except (ValueError, TypeError):
                        lon, lat = cx, cy
                        has_coords = False
                else:
                    lon, lat = cx, cy

                observations.append({
                    "obs_type": "biological",
                    "timestamp": time_start,
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "source_id": f"movebank-study-{rec.get('id', '')}",
                    "source_name": "Movebank",
                    "quality_score": 0.8 if has_coords else 0.5,
                    "payload": {
                        "study_name": rec.get("name", ""),
                        "study_id": rec.get("id"),
                        "taxon": rec.get("taxon_ids", ""),
                        "sensor_types": rec.get("sensor_type_ids", ""),
                        "num_individuals": rec.get("number_of_individuals"),
                        "num_events": rec.get("number_of_events"),
                        "principal_investigator": rec.get("principal_investigator_name", ""),
                        "license_type": rec.get("license_type", ""),
                        "has_exact_location": has_coords,
                    },
                })

        logger.info("Movebank returned %d records", len(observations))
        return observations
