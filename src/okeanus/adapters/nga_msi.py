"""NGA Maritime Safety Information adapter — broadcast warnings, no auth.

The National Geospatial-Intelligence Agency publishes navigational warnings,
NAVAREA messages, and maritime safety broadcasts via a public REST API.

Source: https://msi.nga.mil/
API docs: https://msi.nga.mil/api/swagger-ui.html

Note: The former ASAM (Anti-Shipping Activity Messages) endpoint was removed.
This adapter now uses the broadcast-warn endpoint for navigational warnings.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BROADCAST_WARN_URL = "https://msi.nga.mil/api/publications/broadcast-warn"

# Pattern for coordinates embedded in warning text, e.g. "14-51.78N 061-18.18W"
_COORD_RE = re.compile(
    r"(\d{1,3})-(\d{1,2}(?:\.\d+)?)([NS])\s+(\d{1,3})-(\d{1,2}(?:\.\d+)?)([EW])"
)


def _extract_coords(text: str) -> tuple[float, float] | None:
    """Extract first lat/lon from NGA coordinate format in text."""
    m = _COORD_RE.search(text)
    if not m:
        return None
    lat = float(m.group(1)) + float(m.group(2)) / 60.0
    if m.group(3) == "S":
        lat = -lat
    lon = float(m.group(4)) + float(m.group(5)) / 60.0
    if m.group(6) == "W":
        lon = -lon
    return lat, lon


def _parse_issue_date(s: str) -> datetime | None:
    """Parse NGA issue date format like '081653Z MAY 2024'."""
    if not s:
        return None
    # Format: DDHHMM'Z' MON YYYY
    m = re.match(r"(\d{2})(\d{2})(\d{2})Z\s+(\w{3})\s+(\d{4})", s.strip())
    if m:
        day, hour, minute = int(m.group(1)), int(m.group(2)), int(m.group(3))
        mon_str, year = m.group(4), int(m.group(5))
        months = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
        }
        month = months.get(mon_str.upper())
        if month:
            try:
                return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
            except ValueError:
                pass
    return None


class NgaMsiAdapter(BaseAdapter):
    """Connector for NGA broadcast navigational warnings (maritime safety)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "nga_msi"

    @property
    def source_url(self) -> str:
        return "https://msi.nga.mil/"

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
        """Fetch broadcast navigational warnings from NGA MSI.

        Extra params:
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        w, s, e, n = bbox

        try:
            resp = await self._request(
                "GET", BROADCAST_WARN_URL, params={"output": "json"},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("NGA broadcast-warn fetch failed: %s", exc)
            return []

        records = data if isinstance(data, list) else data.get("broadcast-warn", [])
        if not isinstance(records, list):
            records = []

        observations: list[dict[str, Any]] = []

        for rec in records:
            if len(observations) >= limit:
                break
            if not isinstance(rec, dict):
                continue

            # Parse issue date
            ts = _parse_issue_date(rec.get("issueDate", ""))
            if ts is None:
                continue
            # Active warnings (status=A) are included regardless of date
            # since they represent current navigational hazards
            is_active = rec.get("status", "").upper() == "A"
            if not is_active and (ts < time_start or ts > time_end):
                continue

            # Extract coordinates from warning text
            text = rec.get("text", "")
            coords = _extract_coords(text)
            geometry = None
            if coords:
                lat, lon = coords
                if w <= lon <= e and s <= lat <= n:
                    geometry = {"type": "Point", "coordinates": [lon, lat]}
                else:
                    continue  # Outside bbox
            # Warnings without parseable coords are still useful — skip bbox filter

            nav_area = rec.get("navArea", rec.get("area", ""))
            msg_num = rec.get("msgNumber", rec.get("number", ""))
            msg_year = rec.get("msgYear", rec.get("year", ""))
            ref = f"NAVAREA{nav_area}-{msg_year}-{msg_num}"

            observations.append({
                "obs_type": "maritime_security",
                "timestamp": ts,
                "geometry": geometry,
                "source_id": f"nga-warn-{ref}",
                "source_name": "NGA MSI Broadcast Warnings",
                "quality_score": 1.0,
                "payload": {
                    "reference": ref,
                    "nav_area": nav_area,
                    "subregion": rec.get("subregion", ""),
                    "status": rec.get("status", ""),
                    "authority": rec.get("authority", ""),
                    "text": text[:2000],
                    "issue_date": rec.get("issueDate", ""),
                    "cancel_date": rec.get("cancelDate"),
                },
            })

        logger.info("NGA MSI returned %d broadcast warnings", len(observations))
        return observations
