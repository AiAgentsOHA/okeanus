"""NOAA Incident News adapter — oil spill and hazmat incidents since 1970s.

Downloads the complete CSV of incidents from NOAA's Office of Response and
Restoration. Covers oil spills, chemical releases, and other coastal
environmental incidents where NOAA provided support. No auth required.

Source: https://incidentnews.noaa.gov/
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

CSV_URL = "https://incidentnews.noaa.gov/raw/incidents.csv"


class NoaaIncidentNewsAdapter(BaseAdapter):
    """Connector for NOAA Incident News oil spill / hazmat database."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_incident_news"

    @property
    def source_url(self) -> str:
        return "https://incidentnews.noaa.gov/"

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
        """Fetch oil spill / hazmat incidents from NOAA Incident News.

        Extra params:
            threat: Filter by threat type ('Oil', 'Chemical', etc.)
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        threat_filter = params.get("threat", "").lower()
        w, s, e, n = bbox

        try:
            resp = await self._request("GET", CSV_URL)
            text = resp.text
        except Exception as exc:
            logger.error("NOAA Incident News fetch failed: %s", exc)
            return []

        observations: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            if len(observations) >= limit:
                break

            # Parse date
            date_str = row.get("open_date", row.get("Open Date", ""))
            ts = _parse_date(date_str)
            if ts is None:
                continue

            if ts < time_start or ts > time_end:
                continue

            # Parse coordinates
            lat_str = row.get("lat", row.get("Latitude", ""))
            lon_str = row.get("lon", row.get("Longitude", ""))
            geometry = None
            if lat_str and lon_str:
                try:
                    lat, lon = float(lat_str), float(lon_str)
                    if w <= lon <= e and s <= lat <= n:
                        geometry = {"type": "Point", "coordinates": [lon, lat]}
                    else:
                        continue
                except (ValueError, TypeError):
                    pass

            # Apply threat filter
            threat = row.get("threat", row.get("Threat", ""))
            if threat_filter and threat_filter not in threat.lower():
                continue

            name = row.get("name", row.get("Name", ""))
            incident_id = row.get("id", row.get("ID", ""))
            commodity = row.get("commodity", row.get("Commodity", ""))
            max_release = row.get("max_ptl_release_gallons",
                                  row.get("Max Coverage", ""))
            tags = row.get("tags", row.get("Tags", ""))

            observations.append({
                "obs_type": "environmental_incident",
                "timestamp": ts,
                "geometry": geometry,
                "source_id": f"noaa-incident-{incident_id}",
                "source_name": "NOAA Incident News",
                "quality_score": 0.95,
                "payload": {
                    "incident_id": incident_id,
                    "name": name,
                    "threat": threat,
                    "commodity": commodity,
                    "max_release_gallons": max_release,
                    "tags": tags,
                    "location": row.get("location", row.get("Location", "")),
                },
            })

        logger.info("NOAA Incident News returned %d incidents", len(observations))
        return observations


def _parse_date(s: str | None) -> datetime | None:
    """Parse various date formats from the CSV."""
    if not s:
        return None
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(s).strip()[:19], fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None
