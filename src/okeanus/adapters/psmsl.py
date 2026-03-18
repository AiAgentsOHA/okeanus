"""PSMSL (Permanent Service for Mean Sea Level) adapter.

2,300+ tide gauge stations with monthly mean sea level records since 1807.
Uses flat file downloads (no JSON API). No auth required.

Data portal: https://psmsl.org/data/obtaining/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

FILELIST_URL = "https://psmsl.org/data/obtaining/rlr.monthly.data/filelist.txt"
DATA_URL = "https://psmsl.org/data/obtaining/rlr.monthly.data"


class PsmslAdapter(BaseAdapter):
    """Connector for PSMSL tide gauge sea level data (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "psmsl"

    @property
    def source_url(self) -> str:
        return "https://psmsl.org/"

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
        w, s, e, n = bbox
        limit = params.get("limit", 20)

        # Fetch station list (semicolon-delimited)
        try:
            resp = await self._request("GET", FILELIST_URL)
            text = resp.text
        except Exception as exc:
            logger.error("PSMSL station fetch failed: %s", exc)
            return []

        # Parse: id;lat;lon;name;coastline;station_code;qc_flag
        matching = []
        for line in text.strip().split("\n"):
            parts = line.split(";")
            if len(parts) < 4:
                continue
            try:
                sid = parts[0].strip()
                lat = float(parts[1].strip())
                lon = float(parts[2].strip())
                name = parts[3].strip()
            except (ValueError, IndexError):
                continue
            if w <= lon <= e and s <= lat <= n:
                matching.append({"id": sid, "lat": lat, "lon": lon, "name": name,
                                 "coastline": parts[4].strip() if len(parts) > 4 else "",
                                 "qc": parts[6].strip() if len(parts) > 6 else ""})
            if len(matching) >= limit:
                break

        observations: list[dict[str, Any]] = []
        # Fetch data for a few stations
        for st in matching[:min(limit, 10)]:
            try:
                resp = await self._request("GET", f"{DATA_URL}/{st['id']}.rlrdata")
                lines = resp.text.strip().split("\n")
            except Exception:
                lines = []

            recent = None
            latest_any = None
            for line in lines:
                parts = line.split(";") if ";" in line else line.split()
                if len(parts) < 2:
                    continue
                try:
                    dec_year = float(parts[0].strip())
                    value = float(parts[1].strip())
                    if value < -90000:  # Missing data flag
                        continue
                    yr = int(dec_year)
                    mo = max(1, min(12, round((dec_year - yr) * 12) + 1))
                    ts = datetime(yr, mo, 1)
                except (ValueError, TypeError):
                    continue
                # Track latest record regardless of time filter
                if latest_any is None or ts > latest_any["ts"]:
                    latest_any = {"ts": ts, "value": value}
                # Also track within requested time range
                t_start = time_start.replace(tzinfo=None) if time_start.tzinfo else time_start
                t_end = time_end.replace(tzinfo=None) if time_end.tzinfo else time_end
                if t_start <= ts <= t_end:
                    if recent is None or ts > recent["ts"]:
                        recent = {"ts": ts, "value": value}

            # Prefer time-filtered, fall back to latest available
            best = recent or latest_any
            ts = best["ts"] if best else time_start
            msl = best["value"] if best else None

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [st["lon"], st["lat"]]},
                "source_id": f"psmsl-{st['id']}",
                "source_name": "PSMSL",
                "quality_score": 0.95,
                "payload": {
                    "station_id": st["id"],
                    "station_name": st["name"],
                    "coastline_code": st.get("coastline", ""),
                    "mean_sea_level_mm": msl,
                    "quality_flag": st.get("qc", ""),
                },
            })

        logger.info("PSMSL returned %d tide gauge stations", len(observations))
        return observations
