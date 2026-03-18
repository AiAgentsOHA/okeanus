"""CCHDO/GO-SHIP adapter — global hydrographic cruise data.

CCHDO (CLIVAR and Carbon Hydrographic Data Office) archives
high-quality full-depth hydrographic data from repeat
hydrographic sections (GO-SHIP program).

API: REST at cchdo.ucsd.edu. No auth required.
The list endpoint (``/api/v1/cruise``) returns only ``{expocode, id}``
stubs. Full metadata (geometry, dates, participants) must be fetched
per-cruise from ``/api/v1/cruise/{id}``.

Data source: https://cchdo.ucsd.edu/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://cchdo.ucsd.edu/api/v1"


class CchdoGoshipAdapter(BaseAdapter):
    """Connector for CCHDO/GO-SHIP hydrographic data (no auth required).

    Returns cruise metadata, station data, and hydrographic
    profiles from repeat ocean sections.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=10.0, timeout=25.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "cchdo_goship"

    @property
    def source_url(self) -> str:
        return "https://cchdo.ucsd.edu/"

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
        """Fetch CCHDO cruise/station data within bbox and time range.

        The CCHDO API has no search/filter endpoint so we:
          1. GET ``/api/v1/cruise`` for the full cruise stub list
          2. Fetch individual cruise details in batches
          3. Filter by bbox (first track coordinate) and date

        Extra params:
            expocode: specific cruise identifier (skips the list step)
            limit: max records (default 100)
            batch_size: how many cruise details to fetch (default 200)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 20)
        expocode = params.get("expocode")
        batch_size = params.get("batch_size", 80)

        # --- fast path: single expocode ---
        if expocode:
            return await self._fetch_single(expocode, bbox, time_start, time_end)

        # --- Step 1: get the full cruise stub list ---
        try:
            resp = await self._request("GET", f"{BASE_URL}/cruise")
            data = resp.json()
        except Exception as exc:
            logger.error("CCHDO cruise list failed: %s", exc)
            return []

        cruises = data.get("cruises", []) if isinstance(data, dict) else data
        if not isinstance(cruises, list):
            cruises = []

        # --- Step 2: fetch cruise details in a batch ---
        # We sample from the list (it is not time-sorted) to keep
        # network usage bounded.
        sample = cruises[:batch_size]

        observations: list[dict[str, Any]] = []

        # Fetch details concurrently in small groups
        chunk_size = 20
        for i in range(0, len(sample), chunk_size):
            chunk = sample[i : i + chunk_size]
            tasks = [
                self._fetch_cruise_detail(stub, bbox, time_start, time_end)
                for stub in chunk
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict):
                    observations.append(result)
                    if len(observations) >= limit:
                        break
            if len(observations) >= limit:
                break

        logger.info("CCHDO returned %d cruises", len(observations))
        return observations

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    async def _fetch_single(
        self,
        expocode: str,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch a single cruise by expocode."""
        # The API does not support lookup by expocode directly; scan
        # the list for the numeric id.
        try:
            resp = await self._request("GET", f"{BASE_URL}/cruise")
            stubs = resp.json().get("cruises", [])
        except Exception as exc:
            logger.error("CCHDO cruise list failed: %s", exc)
            return []

        for stub in stubs:
            if stub.get("expocode") == expocode:
                obs = await self._fetch_cruise_detail(stub, bbox, time_start, time_end)
                return [obs] if isinstance(obs, dict) else []
        return []

    async def _fetch_cruise_detail(
        self,
        stub: dict[str, Any],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> dict[str, Any] | None:
        """Fetch full detail for one cruise and return an observation
        dict, or *None* if the cruise is outside the bbox/time."""
        w, s, e, n = bbox
        cid = stub.get("id")
        if cid is None:
            return None

        try:
            resp = await self._request("GET", f"{BASE_URL}/cruise/{cid}")
            cruise = resp.json()
        except Exception:
            return None

        if not isinstance(cruise, dict):
            return None

        # --- extract first track coordinate ---
        geometry = cruise.get("geometry", {})
        track = geometry.get("track", {})
        coords = track.get("coordinates", [])

        if not coords:
            return None

        # coords is [[lon, lat], ...] for a LineString
        first = coords[0]
        if isinstance(first, (list, tuple)) and len(first) >= 2:
            lon, lat = float(first[0]), float(first[1])
        else:
            return None

        # Check bbox — any track point inside is fine
        in_bbox = False
        for pt in coords:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                plon, plat = float(pt[0]), float(pt[1])
                if w <= plon <= e and s <= plat <= n:
                    in_bbox = True
                    lon, lat = plon, plat
                    break
        if not in_bbox:
            return None

        # --- date filter ---
        expo = cruise.get("expocode") or stub.get("expocode", "")
        date_str = cruise.get("startDate", "")
        try:
            ts = datetime.fromisoformat(date_str[:10]) if date_str else None
        except (ValueError, TypeError):
            ts = None

        if ts is not None:
            # Make tz-aware for comparison
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            ts_start = time_start if time_start.tzinfo else time_start.replace(tzinfo=timezone.utc)
            ts_end = time_end if time_end.tzinfo else time_end.replace(tzinfo=timezone.utc)
            if ts < ts_start or ts > ts_end:
                return None

        # --- extract participants / chief scientist ---
        participants = cruise.get("participants", [])
        chief = ""
        for p in participants:
            if isinstance(p, dict) and p.get("role") == "Chief Scientist":
                chief = p.get("name", "")
                break

        return {
            "obs_type": "physical",
            "timestamp": ts or time_start,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "source_id": f"cchdo-{expo}",
            "source_name": "CCHDO/GO-SHIP",
            "quality_score": 0.95,
            "payload": {
                "expocode": expo,
                "ship": cruise.get("ship", ""),
                "country": cruise.get("country", ""),
                "chief_scientist": chief,
                "start_date": date_str,
                "end_date": cruise.get("endDate", ""),
                "collections": cruise.get("collections", {}),
            },
        }
