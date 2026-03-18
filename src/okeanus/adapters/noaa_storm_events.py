"""NOAA Storm Events adapter — severe weather events affecting oceans.

Storm events from NOAA's Severe Weather Data Inventory (SWDI) and the
Storm Events Database. Covers marine weather events like tropical
cyclones, waterspouts, and coastal floods. No auth required.

Data source: https://www.ncdc.noaa.gov/stormevents/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

IBTRACS_ERDDAP = "https://erddap.aoml.noaa.gov/hdb/erddap/tabledap/IBTRACS_last3years"
# Storm Events bulk CSVs at NCEI — by year
BULK_CSV_BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles"

# Marine-relevant event types
MARINE_EVENTS = {
    "Marine Thunderstorm Wind", "Marine Strong Wind", "Marine High Wind",
    "Marine Hail", "Waterspout", "Tropical Storm", "Hurricane",
    "Hurricane (Typhoon)", "Tropical Depression", "Storm Surge/Tide",
    "Coastal Flood", "Tsunami", "Rip Current", "Sneakerwave",
    "High Surf", "Marine Dense Fog",
}


class NoaaStormEventsAdapter(BaseAdapter):
    """Connector for NOAA Storm Events + IBTrACS tropical cyclones (no auth).

    Uses IBTrACS ERDDAP for tropical cyclone tracks (primary) and
    NCEI bulk CSV for other marine storm events (fallback).
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "noaa_storm_events"

    @property
    def source_url(self) -> str:
        return "https://www.ncdc.noaa.gov/stormevents/"

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
        """Fetch tropical cyclone tracks from IBTrACS.

        Extra params:
            source: 'ibtracs' (default) — tropical cyclone best tracks
            basin: 'NA', 'EP', 'WP', 'NI', 'SI', 'SP', 'SA' or 'ALL'
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        basin = params.get("basin")

        ts_start = time_start.strftime("%Y-%m-%dT00:00:00Z")
        ts_end = time_end.strftime("%Y-%m-%dT00:00:00Z")

        # Use IBTrACS on AOML ERDDAP for tropical cyclone data
        # Note: 'time' is numeric (filterable), 'iso_time' is String (display only)
        # AOML ERDDAP requires URL-encoded operators (%3E= for >=, %3C= for <=)
        constraints = (
            f"&time%3E={ts_start}&time%3C={ts_end}"
            f"&latitude%3E={s}&latitude%3C={n}"
            f"&longitude%3E={w}&longitude%3C={e}"
        )
        if basin:
            constraints += f'&basin=%22{basin}%22'

        url = (
            f"{IBTRACS_ERDDAP}.csv"
            f"?sid,name,iso_time,latitude,longitude,usa_wind,usa_pres,"
            f"usa_sshs,basin,nature,dist2land"
            f"{constraints}"
            f"&orderBy(%22iso_time%22)"
        )

        try:
            resp = await self._request("GET", url)
            text = resp.text
        except Exception as exc:
            logger.error("IBTrACS fetch failed: %s", exc)
            return []

        lines = text.strip().split("\n")
        if len(lines) < 3:
            return []

        headers = [h.strip() for h in lines[0].split(",")]
        observations: list[dict[str, Any]] = []

        for line in lines[2:]:  # Skip units row
            if len(observations) >= limit:
                break

            parts = line.split(",")
            if len(parts) < len(headers):
                continue

            row = dict(zip(headers, parts))

            try:
                lat = float(row.get("latitude", "0"))
                lon = float(row.get("longitude", "0"))
            except (ValueError, TypeError):
                continue

            date_str = row.get("iso_time", "")
            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00").strip()) if date_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            wind = row.get("usa_wind", "")
            pres = row.get("usa_pres", "")
            sshs = row.get("usa_sshs", "")

            def _float(v: str) -> float | None:
                try:
                    val = float(v.strip()) if v and v.strip() not in ("", "NaN", " ") else None
                    return val
                except (ValueError, TypeError):
                    return None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"ibtracs-{row.get('sid', '').strip()}-{ts.strftime('%Y%m%d%H')}",
                "source_name": "NOAA IBTrACS",
                "quality_score": 0.9,
                "payload": {
                    "storm_name": row.get("name", "").strip(),
                    "storm_id": row.get("sid", "").strip(),
                    "basin": row.get("basin", "").strip(),
                    "nature": row.get("nature", "").strip(),
                    "wind_kt": _float(wind),
                    "pressure_mb": _float(pres),
                    "saffir_simpson": _float(sshs),
                    "dist_to_land_km": _float(row.get("dist2land", "")),
                },
            })

        logger.info("IBTrACS returned %d storm track points", len(observations))
        return observations
