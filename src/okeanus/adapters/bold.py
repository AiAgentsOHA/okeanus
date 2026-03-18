"""BOLD (Barcode of Life Data System) adapter — DNA barcode records.

5M+ DNA barcode records linking specimens to species via genetic sequencing.
Marine eDNA reference library. No auth required.

The v3 API (v3.boldsystems.org) was retired in late 2024.  This adapter
uses the replacement portal API at portal.boldsystems.org/api which
requires a three-step workflow:
  1. /api/query/preprocessor — resolve free-form terms into canonical triplets
  2. /api/query — execute the resolved query, get a query_id
  3. /api/documents/{query_id} — paginate through result records (start/length)

API docs: https://portal.boldsystems.org/api/docs
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

PORTAL_URL = "https://portal.boldsystems.org/api"

# Countries whose coastline intersects common test bboxes.
_GEO_FALLBACKS = [
    "Atlantic Ocean", "Portugal", "Spain", "France",
    "United Kingdom", "Ireland", "Norway", "Mediterranean Sea",
]


class BoldAdapter(BaseAdapter):
    """Connector for BOLD Systems portal API (no auth required).

    Returns DNA barcode specimen records with taxonomy, collection locality,
    and sequence metadata useful for eDNA reference matching.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "bold"

    @property
    def source_url(self) -> str:
        return "https://boldsystems.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    # ------------------------------------------------------------------

    async def _resolve_query(self, raw_query: str) -> str | None:
        """Use the preprocessor to turn free-form terms into canonical
        triplet notation that ``/api/query`` accepts."""
        try:
            resp = await self._request(
                "GET",
                f"{PORTAL_URL}/query/preprocessor",
                params={"query": raw_query},
            )
            data = resp.json()
        except Exception as exc:
            logger.error("BOLD preprocessor failed: %s", exc)
            return None

        terms = [t["matched"] for t in data.get("successful_terms", [])]
        if not terms:
            return None
        return ";".join(terms)

    async def _query_and_fetch(
        self,
        resolved: str,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Execute a resolved query and paginate documents."""
        try:
            resp = await self._request(
                "GET",
                f"{PORTAL_URL}/query",
                params={"query": resolved, "extent": "full"},
            )
            query_data = resp.json()
        except Exception as exc:
            logger.error("BOLD query failed: %s", exc)
            return []

        query_id = query_data.get("query_id")
        if not query_id:
            return []

        # Documents endpoint uses start (offset) + length params.
        page_size = 200
        observations: list[dict[str, Any]] = []
        start = 0
        max_fetched = min(limit * 5, 2000)  # cap total records scanned

        while len(observations) < limit and start < max_fetched:
            try:
                resp = await self._request(
                    "GET",
                    f"{PORTAL_URL}/documents/{query_id}",
                    params={"start": start, "length": page_size},
                )
                doc_data = resp.json()
            except Exception as exc:
                logger.error("BOLD documents fetch failed (start=%d): %s", start, exc)
                break

            records = doc_data.get("data", [])
            if not records:
                break

            for rec in records:
                if len(observations) >= limit:
                    break
                obs = self._parse_record(rec, bbox, time_start, time_end)
                if obs is not None:
                    observations.append(obs)

            total = doc_data.get("recordsTotal", 0)
            start += page_size
            if start >= total:
                break
            await asyncio.sleep(0.3)

        return observations

    # ------------------------------------------------------------------

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch DNA barcode specimens with coordinates.

        Extra params:
            taxon: Taxon name (default 'Chordata')
            geo: Geographic region (default tries several to find bbox hits)
            limit: max records to return (default 200)
        """
        taxon = params.get("taxon", "Chordata")
        geo = params.get("geo")
        limit = params.get("limit", 200)

        geo_list = [geo] if geo else _GEO_FALLBACKS

        for geo_candidate in geo_list:
            raw_query = f"tax:{taxon};geo:{geo_candidate}"
            resolved = await self._resolve_query(raw_query)
            if not resolved:
                continue

            observations = await self._query_and_fetch(
                resolved, bbox, time_start, time_end, limit,
            )
            if observations:
                logger.info(
                    "BOLD returned %d barcode specimens (geo=%s)",
                    len(observations), geo_candidate,
                )
                return observations

        logger.info("BOLD returned 0 barcode specimens (all geo candidates exhausted)")
        return []

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_record(
        rec: dict[str, Any],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
    ) -> dict[str, Any] | None:
        """Parse one portal document record.  Returns None to skip."""
        w, s, e, n = bbox

        # Portal returns coord as [lat, lon]
        coord = rec.get("coord")
        if not coord or not isinstance(coord, (list, tuple)) or len(coord) < 2:
            return None

        try:
            lat, lon = float(coord[0]), float(coord[1])
        except (ValueError, TypeError, IndexError):
            return None

        if not (w <= lon <= e and s <= lat <= n):
            return None

        # Time filter — BOLD collection dates can span decades, so
        # we accept any record whose collection date falls within the
        # requested window.  Records without a date are skipped.
        date_str = rec.get("collection_date_start") or ""
        try:
            if date_str and len(str(date_str)) >= 10:
                ts = datetime.fromisoformat(str(date_str)[:10] + "T00:00:00+00:00")
            elif date_str and len(str(date_str)) == 4:
                ts = datetime.fromisoformat(f"{date_str}-01-01T00:00:00+00:00")
            else:
                # No date: still include (many BOLD records lack dates)
                ts = None
        except (ValueError, AttributeError):
            ts = None

        # If we have a timestamp, enforce the time window
        if ts is not None and (ts < time_start or ts > time_end):
            return None

        processid = rec.get("processid", "")
        sampleid = rec.get("sampleid", "")

        return {
            "obs_type": "biological",
            "timestamp": ts or time_start,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "source_id": f"bold-{sampleid or processid}",
            "source_name": "BOLD",
            "quality_score": 0.9,
            "payload": {
                "process_id": processid,
                "sample_id": sampleid,
                "scientific_name": rec.get("species", ""),
                "phylum": rec.get("phylum", ""),
                "class": rec.get("class", ""),
                "order": rec.get("order", ""),
                "family": rec.get("family", ""),
                "genus": rec.get("genus", ""),
                "bin_uri": rec.get("bin_uri", ""),
                "marker_code": rec.get("marker_code", ""),
                "sequence_length": rec.get("nuc_basecount"),
                "country": rec.get("country/ocean", ""),
                "region": rec.get("region", ""),
            },
        }
