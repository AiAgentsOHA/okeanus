"""NOAA ERMA adapter — Environmental Response Management Application.

NOAA's ERMA provides geospatial data for environmental incidents including
oil spills, chemical releases, and natural hazards.

The legacy ArcGIS endpoint (gis.response.restoration.noaa.gov) was
decommissioned.  This adapter now fetches from the NOAA Incident News
CSV export, which contains the same oil-spill / hazmat incident records
(1970s-present). No auth required.

Data source: https://incidentnews.noaa.gov/
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


class NoaaErmaAdapter(BaseAdapter):
    """Connector for NOAA ERMA / Incident News data (no auth required).

    Fetches environmental incident records from the NOAA Incident News
    CSV export since the original ArcGIS MapServer was retired.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_erma"

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
        """Fetch environmental incident data within bbox.

        Extra params:
            incident_type: filter by type (e.g. 'Oil', 'Chemical')
            limit: max records to return (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        incident_type = (params.get("incident_type") or "").lower()

        try:
            resp = await self._request("GET", CSV_URL)
            text = resp.text
        except Exception as exc:
            logger.error("NOAA ERMA/Incident News fetch failed: %s", exc)
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

            # Parse coordinates & spatial filter
            lat_str = row.get("lat", row.get("Latitude", ""))
            lon_str = row.get("lon", row.get("Longitude", ""))
            if not lat_str or not lon_str:
                continue
            try:
                lat, lon = float(lat_str), float(lon_str)
            except (ValueError, TypeError):
                continue

            if not (w <= lon <= e and s <= lat <= n):
                continue

            # Apply incident type filter
            threat = row.get("threat", row.get("Threat", ""))
            if incident_type and incident_type not in threat.lower():
                continue

            incident_id = row.get("id", row.get("ID", ""))
            name = row.get("name", row.get("Name", ""))
            commodity = row.get("commodity", row.get("Commodity", ""))
            max_release = row.get("max_ptl_release_gallons",
                                  row.get("Max Coverage", ""))
            tags = row.get("tags", row.get("Tags", ""))

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"erma-{incident_id}",
                "source_name": "NOAA ERMA",
                "quality_score": 0.85,
                "payload": {
                    "incident_name": name,
                    "incident_type": threat,
                    "commodity": commodity,
                    "max_release_gallons": max_release,
                    "tags": tags,
                    "location": row.get("location", row.get("Location", "")),
                    "status": "",
                    "description": "",
                },
            })

        logger.info("NOAA ERMA returned %d incidents", len(observations))
        return observations


def _parse_date(s: str | None) -> datetime | None:
    """Parse various date formats from the CSV."""
    if not s:
        return None
    for fmt in ("%m/%d/%Y %H:%M", "%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(s).strip()[:19], fmt).replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            continue
    return None
