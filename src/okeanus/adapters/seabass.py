"""NASA SeaBASS adapter — bio-optical oceanographic archive.

SeaBASS (SeaWiFS Bio-optical Archive and Storage System) hosts in situ
bio-optical and biogeochemical measurements used for satellite ocean color
validation. No auth required for archive browsing.

Data source: https://seabass.gsfc.nasa.gov/

Note: SeaBASS has no public REST/JSON API. The search form requires
JavaScript execution. This adapter scrapes the public archive listing
to enumerate available experiments/cruises.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://seabass.gsfc.nasa.gov/archive/"


class SeaBassAdapter(BaseAdapter):
    """Connector for NASA SeaBASS bio-optical archive (scrapes archive listing)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=60.0, **kwargs)

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
        """Scrape SeaBASS archive listing for experiment/cruise catalog.

        Returns experiment-level records from the public archive directory.
        Individual file search requires the SeaBASS web UI (JS-driven).

        Extra params:
            limit: max records (default 200)
        """
        limit = params.get("limit", 200)

        try:
            resp = await self._request("GET", ARCHIVE_URL)
            html = resp.text
        except Exception as exc:
            logger.error("SeaBASS archive fetch failed: %s", exc)
            return []

        # Parse experiment directories from the archive listing
        # Links look like: href="/archive/AWI" (no trailing slash)
        experiments = re.findall(r'href="/archive/([A-Za-z0-9_][^"]*)"', html)

        observations: list[dict[str, Any]] = []

        for exp_name in experiments[:limit]:
            if exp_name.startswith(".") or exp_name in ("css", "js", "images"):
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": time_start,
                "geometry": None,
                "source_id": f"seabass-exp-{exp_name}",
                "source_name": "NASA SeaBASS",
                "quality_score": 0.7,
                "payload": {
                    "experiment": exp_name,
                    "archive_url": f"{ARCHIVE_URL}{exp_name}/",
                    "note": "Experiment-level catalog entry; use SeaBASS web UI for file-level search",
                },
            })

        logger.info("SeaBASS returned %d experiment records", len(observations))
        return observations
