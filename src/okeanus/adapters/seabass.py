"""NASA SeaBASS adapter — bio-optical oceanographic archive.

SeaBASS (SeaWiFS Bio-optical Archive and Storage System) hosts in situ
bio-optical and biogeochemical measurements used for satellite ocean color
validation. No auth required for search; download may require Earthdata.

Data source: https://seabass.gsfc.nasa.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://seabass.gsfc.nasa.gov/api/file_search"


class SeaBassAdapter(BaseAdapter):
    """Connector for NASA SeaBASS bio-optical archive (no auth for search)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "seabass"

    @property
    def source_url(self) -> str:
        return "https://seabass.gsfc.nasa.gov/"

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
        """Search SeaBASS for bio-optical data within bbox and time range.

        Extra params:
            measurement: filter by measurement type (e.g. 'Rrs', 'chlor_a', 'aph')
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        measurement = params.get("measurement")

        api_params: dict[str, Any] = {
            "sdate": time_start.strftime("%Y%m%d"),
            "edate": time_end.strftime("%Y%m%d"),
            "slat": s,
            "elat": n,
            "slon": w,
            "elon": e,
            "results_as": "search",
        }

        if measurement:
            api_params["search"] = measurement

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("SeaBASS fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("results", [])
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            lon = rec.get("lon", rec.get("longitude"))
            lat = rec.get("lat", rec.get("latitude"))
            if lon is None or lat is None:
                continue

            try:
                lon, lat = float(lon), float(lat)
            except (ValueError, TypeError):
                continue

            date_str = rec.get("date", rec.get("start_date", ""))
            try:
                ts = datetime.strptime(str(date_str), "%Y%m%d") if date_str else time_start
            except ValueError:
                ts = time_start

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"seabass-{rec.get('filename', rec.get('id', ''))}",
                "source_name": "NASA SeaBASS",
                "quality_score": 0.9,
                "payload": {
                    "filename": rec.get("filename", ""),
                    "experiment": rec.get("experiment", ""),
                    "cruise": rec.get("cruise", ""),
                    "station": rec.get("station", ""),
                    "water_depth_m": rec.get("water_depth"),
                    "measurements": rec.get("measurements", rec.get("fields", "")),
                    "pi": rec.get("investigators", rec.get("pi", "")),
                    "affiliations": rec.get("affiliations", ""),
                },
            })

        logger.info("SeaBASS returned %d records", len(observations))
        return observations
