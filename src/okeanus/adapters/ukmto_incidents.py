"""UKMTO (United Kingdom Maritime Trade Operations) adapter.

UKMTO provides maritime security reporting for the Arabian Gulf,
Strait of Hormuz, Gulf of Aden, Red Sea, Indian Ocean, and
surrounding waters. Voluntary reporting scheme for merchant vessels.

The website at ukmto.org is behind Cloudflare protection which blocks
standard HTTP clients. This adapter uses Scrapling's StealthyFetcher
to bypass Cloudflare and parse rendered incident data from the
Next.js-based recent-incidents page.

Data source: https://www.ukmto.org/recent-incidents
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.ukmto.org"


class UkmtoIncidentsAdapter(BaseAdapter):
    """Connector for UKMTO maritime security incidents.

    Uses Scrapling StealthyFetcher to bypass Cloudflare protection,
    then parses incident data from the rendered HTML content.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=90.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ukmto_incidents"

    @property
    def source_url(self) -> str:
        return "https://www.ukmto.org/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    @staticmethod
    def _parse_incidents_from_html(html: str) -> list[dict[str, Any]]:
        """Extract structured incident data from UKMTO rendered HTML.

        The page lists incidents as sections with headers like:
            'Attack UKMTO #22', 'Suspicious Activity UKMTO #17'
        followed by description text containing location, date, and details.
        """
        # Remove style and script tags
        clean = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        clean = re.sub(r"<script[^>]*>.*?</script>", "", clean, flags=re.DOTALL)
        # Replace HTML tags with newlines
        clean = re.sub(r"<[^>]+>", "\n", clean)
        clean = re.sub(r"\n\s*\n", "\n", clean)
        clean = re.sub(r"[ \t]+", " ", clean)

        lines = [line.strip() for line in clean.split("\n") if line.strip()]

        incidents: list[dict[str, Any]] = []
        # Pattern to match incident headers like "Attack UKMTO #22" or
        # "Suspicious Activity UKMTO #17"
        header_pattern = re.compile(
            r"^(Attack|Suspicious Activity|Advisory|Warning)\s+"
            r"UKMTO\s+#(\d+)",
            re.IGNORECASE,
        )

        # Date pattern: DD/MM/YYYY or DDMMMYY or similar
        date_pattern = re.compile(
            r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})"
        )
        date_pattern_alt = re.compile(
            r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{2,4})",
            re.IGNORECASE,
        )

        current_incident: dict[str, Any] | None = None
        current_text_lines: list[str] = []

        def flush_incident() -> None:
            nonlocal current_incident, current_text_lines
            if current_incident is not None:
                current_incident["description"] = " ".join(current_text_lines).strip()
                incidents.append(current_incident)
            current_incident = None
            current_text_lines = []

        for line in lines:
            m = header_pattern.match(line)
            if m:
                flush_incident()
                current_incident = {
                    "incident_type": m.group(1).strip().lower(),
                    "incident_number": int(m.group(2)),
                    "date": None,
                    "location_text": "",
                }
                continue

            if current_incident is not None:
                current_text_lines.append(line)

                # Try to extract date
                if current_incident["date"] is None:
                    dm = date_pattern.search(line)
                    if dm:
                        try:
                            day, month, year = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
                            current_incident["date"] = datetime(year, month, day)
                        except (ValueError, TypeError):
                            pass
                    else:
                        dm2 = date_pattern_alt.search(line)
                        if dm2:
                            month_names = {
                                "jan": 1, "feb": 2, "mar": 3, "apr": 4,
                                "may": 5, "jun": 6, "jul": 7, "aug": 8,
                                "sep": 9, "oct": 10, "nov": 11, "dec": 12,
                            }
                            try:
                                day = int(dm2.group(1))
                                month = month_names[dm2.group(2).lower()[:3]]
                                year = int(dm2.group(3))
                                if year < 100:
                                    year += 2000
                                current_incident["date"] = datetime(year, month, day)
                            except (ValueError, TypeError, KeyError):
                                pass

                # Try to extract location description
                loc_patterns = [
                    r"(\d+NM\s+\w+\s+of\s+[^,.]+)",
                    r"(north|south|east|west|northwest|northeast|southwest|southeast)\s+of\s+([^,.]+)",
                    r"(Straits?\s+of\s+Hormuz|Gulf\s+of\s+(?:Aden|Oman)|Red\s+Sea|Arabian\s+(?:Gulf|Sea)|Indian\s+Ocean)",
                    r"(Port\s+of\s+\w+)",
                ]
                for pat in loc_patterns:
                    lm = re.search(pat, line, re.IGNORECASE)
                    if lm and not current_incident["location_text"]:
                        current_incident["location_text"] = lm.group(0).strip()

        flush_incident()
        return incidents

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch UKMTO maritime security incidents.

        Uses Scrapling StealthyFetcher to bypass Cloudflare protection
        on ukmto.org, then parses incident data from the rendered HTML.

        Extra params:
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)

        html = ""
        # Strategy 1: Scrapling StealthyFetcher (bypasses Cloudflare)
        # Scrapling uses Playwright's sync API internally, so we must
        # run it in a thread executor to avoid blocking the event loop
        # and to avoid the "sync API inside asyncio loop" error.
        try:
            import asyncio
            from scrapling import StealthyFetcher

            def _scrape() -> str:
                fetcher = StealthyFetcher()
                response = fetcher.fetch(f"{BASE_URL}/recent-incidents")
                if response.status == 200:
                    return response.html_content
                return ""

            html = await asyncio.to_thread(_scrape)
            if html:
                logger.info("UKMTO: Scrapling fetched %d bytes", len(html))
        except ImportError:
            logger.warning(
                "UKMTO: scrapling not installed. "
                "Install with: pip install scrapling"
            )
        except Exception as exc:
            logger.warning("UKMTO: Scrapling fetch failed: %s", exc)

        # Strategy 2: Plain HTTP (usually blocked by Cloudflare)
        if not html or len(html) < 500:
            for url in [f"{BASE_URL}/recent-incidents", f"{BASE_URL}/"]:
                try:
                    resp = await self._request("GET", url)
                    if resp.status_code == 200 and len(resp.text) > 500:
                        html = resp.text
                        break
                except Exception:
                    continue

        if not html or len(html) < 500:
            logger.warning(
                "UKMTO: all access methods failed (Cloudflare protection). "
                "Incident data available at https://www.ukmto.org/recent-incidents"
            )
            return []

        # Parse incidents from the rendered HTML
        raw_incidents = self._parse_incidents_from_html(html)

        if not raw_incidents:
            logger.warning("UKMTO: page fetched but no incidents parsed from HTML")
            return []

        observations: list[dict[str, Any]] = []

        # UKMTO incidents cover Arabian Gulf / Indian Ocean region.
        # Use centroid of the operational area as default coordinates
        # since exact coordinates are not always in the rendered text.
        default_lat = 24.0  # Central Arabian Gulf / Gulf of Oman
        default_lon = 56.0

        for inc in raw_incidents:
            if len(observations) >= limit:
                break

            ts = inc.get("date") or time_start
            if isinstance(ts, datetime):
                # Ensure tz-aware comparison works: strip tzinfo for comparison
                ts_naive = ts.replace(tzinfo=None)
                start_naive = time_start.replace(tzinfo=None)
                end_naive = time_end.replace(tzinfo=None)
                if ts_naive < start_naive or ts_naive > end_naive:
                    continue

            inc_num = inc.get("incident_number", len(observations))
            inc_type = inc.get("incident_type", "unknown")
            location = inc.get("location_text", "")
            description = inc.get("description", "")

            observations.append({
                "obs_type": "governance",
                "timestamp": ts,
                "geometry": {
                    "type": "Point",
                    "coordinates": [default_lon, default_lat],
                },
                "source_id": f"ukmto-2026-{inc_num}",
                "source_name": "UKMTO",
                "quality_score": 0.75,
                "payload": {
                    "incident_type": inc_type,
                    "incident_number": inc_num,
                    "region": "Arabian Gulf / Strait of Hormuz / Indian Ocean",
                    "location_text": location,
                    "description": description[:500] if description else "",
                    "source_url": f"{BASE_URL}/recent-incidents",
                },
            })

        logger.info("UKMTO returned %d incident reports", len(observations))
        return observations
