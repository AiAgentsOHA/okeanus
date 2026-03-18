"""BSEE Incidents adapter — US Outer Continental Shelf incident reports.

The Bureau of Safety and Environmental Enforcement tracks incidents
on the US OCS. Data available via public ZIP downloads. No auth required.

NOTE: The original SpillsInformation.csv was removed from data.bsee.gov.
This adapter now uses IncInvRawData.zip (incident investigations) enriched
with lat/lon from PlatStrucRawData.zip (platform structures).

Source: https://www.data.bsee.gov/Main/RawData.aspx
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# BSEE raw data ZIPs — updated daily
INCIDENTS_URL = "https://www.data.bsee.gov/Other/Files/IncInvRawData.zip"
PLATFORMS_URL = "https://www.data.bsee.gov/Platform/Files/PlatStrucRawData.zip"


class BseeSpillsAdapter(BaseAdapter):
    """Connector for BSEE OCS incident reports."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=90.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "bsee_spills"

    @property
    def source_url(self) -> str:
        return "https://www.data.bsee.gov/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def _build_location_lookup(self) -> dict[str, tuple[float, float]]:
        """Download platform structures and build area+block → (lat, lon) lookup."""
        try:
            resp = await self._request("GET", PLATFORMS_URL)
        except Exception as exc:
            logger.warning("BSEE platform structures fetch failed: %s", exc)
            return {}

        lookup: dict[str, tuple[float, float]] = {}
        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            for name in zf.namelist():
                if "structures" in name.lower() and not name.endswith("/"):
                    text = zf.read(name).decode("utf-8", errors="replace")
                    reader = csv.DictReader(io.StringIO(text))
                    for row in reader:
                        area = row.get("AREA_CODE", "").strip()
                        block = row.get("BLOCK_NUMBER", "").strip()
                        lat_str = row.get("LATITUDE", "")
                        lon_str = row.get("LONGITUDE", "")
                        if area and block and lat_str and lon_str:
                            try:
                                key = f"{area} {block}"
                                lookup[key] = (float(lat_str), float(lon_str))
                            except (ValueError, TypeError):
                                continue
        except Exception as exc:
            logger.warning("Platform structure parsing failed: %s", exc)

        logger.info("Built location lookup with %d area/block entries", len(lookup))
        return lookup

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch OCS incident reports from BSEE.

        Extra params:
            limit: Max records (default 100)
        """
        limit = params.get("limit", 100)
        w, s, e, n = bbox

        # Download incident investigations ZIP
        try:
            resp = await self._request("GET", INCIDENTS_URL)
        except Exception as exc:
            logger.error("BSEE incidents fetch failed: %s", exc)
            return []

        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
            txt_files = [f for f in zf.namelist() if not f.endswith("/")]
            if not txt_files:
                logger.error("BSEE ZIP contains no data files")
                return []
            text = zf.read(txt_files[0]).decode("utf-8", errors="replace")
        except Exception as exc:
            logger.error("BSEE ZIP extraction failed: %s", exc)
            return []

        # Build location lookup from platform structures
        loc_lookup = await self._build_location_lookup()

        observations: list[dict[str, Any]] = []
        reader = csv.DictReader(io.StringIO(text))

        for row in reader:
            if len(observations) >= limit:
                break

            # Parse date
            date_str = row.get("DATE_OCCURRED", "")
            ts = _parse_date(date_str)
            if ts is None:
                continue

            # Strip tzinfo for comparison if time_start is naive
            ts_cmp = ts.replace(tzinfo=None) if time_start.tzinfo is None else ts
            if ts_cmp < time_start or ts_cmp > time_end:
                continue

            # Look up coordinates from area/block
            area_block = row.get("AREA_BLOCK", "").strip()
            coords = loc_lookup.get(area_block)

            if coords:
                lat, lon = coords
                if not (w <= lon <= e and s <= lat <= n):
                    continue
                geometry = {"type": "Point", "coordinates": [lon, lat]}
            else:
                # No coordinates available — skip if strict bbox filtering
                continue

            accident_type = row.get("ACCIDENT_TYPE", "").strip().strip("-").strip()
            status = row.get("STATUS", "").strip()
            lease = row.get("LEASE_NUMBER", "").strip()
            mil_time = row.get("MILITARY_TIME", "").strip()

            observations.append({
                "obs_type": "oil_spill",
                "timestamp": ts,
                "geometry": geometry,
                "source_id": f"bsee-inc-{lease}-{date_str}",
                "source_name": "BSEE",
                "quality_score": 0.85,
                "payload": {
                    "lease_number": lease,
                    "area_block": area_block,
                    "accident_type": accident_type,
                    "time": mil_time,
                    "status": status,
                    "district": row.get("PANEL_DISTRICT", "").strip(),
                },
            })

        logger.info("BSEE returned %d incident records", len(observations))
        return observations


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(str(s).strip()[:19], fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None
