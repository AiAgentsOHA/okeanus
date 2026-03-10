"""HAEDAT adapter — Harmful Algal Event Database.

Global database of harmful algal bloom (HAB) events maintained by
IOC-UNESCO. Includes bloom location, species, toxins, and impacts.
No auth required.

Data portal: https://haedat.iode.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://haedat.iode.org/api"


class HaedatAdapter(BaseAdapter):
    """Connector for the HAEDAT harmful algal bloom event database."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "haedat"

    @property
    def source_url(self) -> str:
        return "https://haedat.iode.org/"

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
        """Fetch HAB events within bbox and time range.

        Extra params:
            country: Country name filter
            syndrome: e.g. 'PSP', 'DSP', 'ASP', 'CFP', 'NSP'
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "minlon": w,
            "minlat": s,
            "maxlon": e,
            "maxlat": n,
            "startdate": time_start.strftime("%Y-%m-%d"),
            "enddate": time_end.strftime("%Y-%m-%d"),
            "limit": limit,
        }
        if country := params.get("country"):
            api_params["country"] = country
        if syndrome := params.get("syndrome"):
            api_params["syndrome"] = syndrome

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/events", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("HAEDAT fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("events", data.get("results", []))
        observations: list[dict[str, Any]] = []

        for rec in results:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("longitude", rec.get("lon"))
            lat = rec.get("latitude", rec.get("lat"))
            if lon is None or lat is None:
                continue

            date_str = rec.get("eventDate") or rec.get("date") or rec.get("year", "")
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                elif len(str(date_str)) == 4:
                    ts = datetime.fromisoformat(f"{date_str}-01-01T00:00:00+00:00")
                else:
                    ts = datetime.fromisoformat(str(date_str) + "T00:00:00+00:00")
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"haedat-{rec.get('eventID', rec.get('id', ''))}",
                "source_name": "HAEDAT",
                "quality_score": 0.85,
                "payload": {
                    "species": rec.get("causativeSpecies", rec.get("species", "")),
                    "syndrome": rec.get("syndrome", ""),
                    "country": rec.get("country", ""),
                    "area": rec.get("areaName", rec.get("area", "")),
                    "impacts": rec.get("impacts", ""),
                    "toxins": rec.get("toxins", ""),
                    "max_cells_per_l": rec.get("maxCellsPerLitre"),
                    "event_comments": str(rec.get("comments", ""))[:500],
                },
            })

        logger.info("HAEDAT returned %d HAB events", len(observations))
        return observations
