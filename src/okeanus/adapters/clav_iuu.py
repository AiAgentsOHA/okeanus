"""CLAV IUU Vessel List adapter — Combined IUU Vessel List.

Aggregated IUU (Illegal, Unreported, Unregulated) fishing vessel lists
from all RFMOs, maintained by Trygg Mat Tracking (TMT). No auth required.

The site has no REST API -- data is served via an HTML search page.
This adapter scrapes the search results table from the public search
page at https://www.iuu-vessels.org/Home/Search.

Data source: https://www.iuu-vessels.org/
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.iuu-vessels.org/Home/Search"


class ClavIuuAdapter(BaseAdapter):
    """Connector for the Combined IUU Vessel List (no auth required).

    Returns vessels flagged for illegal fishing by RFMOs worldwide.
    No spatial coordinates per se -- vessels are listed by flag state and RFMO.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "clav_iuu"

    @property
    def source_url(self) -> str:
        return "https://www.iuu-vessels.org/"

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
        """Fetch IUU-listed vessels by scraping the HTML search page.

        Since IUU listings don't have coordinates, results are returned
        with geometry at (0, 0). Use vessel identifiers (IMO, name) to
        cross-reference with AIS position data.

        Extra params:
            limit: max records (default 200)
        """
        limit = params.get("limit", 200)

        try:
            resp = await self._request("GET", SEARCH_URL)
            html = resp.text
        except Exception as exc:
            logger.error("CLAV IUU fetch failed: %s", exc)
            return []

        observations = self._parse_html_table(html, limit)
        logger.info("CLAV IUU returned %d listed vessels", len(observations))
        return observations

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_html_table(html: str, limit: int) -> list[dict[str, Any]]:
        """Extract vessel records from the search results HTML table."""
        observations: list[dict[str, Any]] = []

        row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
        cell_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
        tag_strip = re.compile(r"<[^>]+>")

        rows = row_pattern.findall(html)

        for row_html in rows:
            if len(observations) >= limit:
                break

            cells = cell_pattern.findall(row_html)
            if len(cells) < 3:
                continue

            values = [tag_strip.sub("", c).strip() for c in cells]

            # Skip header rows
            if values[0].lower() in ("vessel name", "name", ""):
                continue

            vessel_name = values[0] if len(values) > 0 else ""
            flag = values[1] if len(values) > 1 else ""
            rfmo = values[2] if len(values) > 2 else ""
            listing_date = values[3] if len(values) > 3 else ""
            call_sign = values[4] if len(values) > 4 else ""
            imo = values[5] if len(values) > 5 else ""

            if not vessel_name:
                continue

            ts = datetime.now(timezone.utc)
            if listing_date:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%Y"):
                    try:
                        ts = datetime.strptime(listing_date.strip(), fmt).replace(
                            tzinfo=timezone.utc
                        )
                        break
                    except ValueError:
                        continue

            source_id = f"iuu-{imo or vessel_name}".replace(" ", "_")

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                "source_id": source_id,
                "source_name": "CLAV IUU",
                "quality_score": 0.95,
                "payload": {
                    "vessel_name": vessel_name,
                    "imo": imo,
                    "flag": flag,
                    "rfmo": rfmo,
                    "call_sign": call_sign,
                    "listing_date": listing_date,
                },
            })

        return observations
