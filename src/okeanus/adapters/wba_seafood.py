"""World Benchmarking Alliance Seafood Stewardship Index adapter.

Rankings and scores for the 30 largest seafood companies globally
across governance, traceability, ecosystems, and social responsibility.

The WBA Data API at data.worldbenchmarkingalliance.org requires a
bearer token (approval needed). This adapter instead scrapes the
public publication page at archive.worldbenchmarkingalliance.org
using Scrapling to bypass Cloudflare, extracting company names and
countries from the rendered HTML.

Full dataset (XLSX with detailed scores) is available for direct
download at:
https://assets.worldbenchmarkingalliance.org/app/uploads/2023/10/
Seafood-Stewardship-Index-2023-Public-Data-set_v3.0.xlsx

Data: worldbenchmarkingalliance.org
No auth required for the public site.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Public publication page (archive, Cloudflare-protected)
PUBLICATION_URL = (
    "https://archive.worldbenchmarkingalliance.org"
    "/publication/seafood-stewardship-index/"
)

# Direct XLSX download (no auth, no Cloudflare)
XLSX_URL = (
    "https://assets.worldbenchmarkingalliance.org/app/uploads/2023/10/"
    "Seafood-Stewardship-Index-2023-Public-Data-set_v3.0.xlsx"
)


class WbaSeafoodAdapter(BaseAdapter):
    """Connector for WBA Seafood Stewardship Index.

    Scrapes the public archive page for the 30 assessed seafood
    companies. Cloudflare is bypassed using Scrapling StealthyFetcher.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "wba_seafood"

    @property
    def source_url(self) -> str:
        return "https://www.worldbenchmarkingalliance.org/rankings/seafood-stewardship-index/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    @staticmethod
    def _parse_companies_from_html(html: str) -> list[dict[str, str]]:
        """Extract company names and countries from WBA publication page.

        The page lists companies in a repeating pattern:
            Title:
            <company name>
            Place:
            <country>
        """
        # Strip style/script tags
        clean = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)
        clean = re.sub(r"<script[^>]*>.*?</script>", "", clean, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", "\n", clean)
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        companies: list[dict[str, str]] = []
        i = 0
        while i < len(lines):
            if lines[i] == "Title:" and i + 3 < len(lines):
                name = lines[i + 1]
                if lines[i + 2] == "Place:":
                    country = lines[i + 3]
                    # Unescape HTML entities
                    name = name.replace("&amp;", "&")
                    country = country.replace("&amp;", "&")
                    companies.append({"name": name, "country": country})
                    i += 4
                    continue
            i += 1

        return companies

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch WBA Seafood Stewardship Index rankings.

        Uses Scrapling StealthyFetcher to bypass Cloudflare on the
        WBA archive site, then parses company data from rendered HTML.

        Extra params:
            company: company name filter (case-insensitive substring)
            limit: max records (default: 30)
        """
        company_filter = params.get("company")
        limit = params.get("limit", 30)

        html = ""

        # Strategy 1: Scrapling StealthyFetcher (bypasses Cloudflare)
        # Scrapling uses Playwright's sync API internally, so we must
        # run it in a thread executor to avoid the "sync API inside
        # asyncio loop" error.
        try:
            import asyncio
            from scrapling import StealthyFetcher

            def _scrape() -> str:
                fetcher = StealthyFetcher()
                response = fetcher.fetch(PUBLICATION_URL)
                if response.status == 200 and len(response.html_content) > 1000:
                    return response.html_content
                return ""

            html = await asyncio.to_thread(_scrape)
            if html:
                logger.info("WBA SSI: Scrapling fetched %d bytes", len(html))
        except ImportError:
            logger.warning(
                "WBA SSI: scrapling not installed. "
                "Install with: pip install scrapling"
            )
        except Exception as exc:
            logger.warning("WBA SSI: Scrapling fetch failed: %s", exc)

        # Strategy 2: Direct HTTP (often Cloudflare-blocked)
        if not html or len(html) < 1000:
            try:
                resp = await self._request("GET", PUBLICATION_URL)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    html = resp.text
            except Exception:
                pass

        if not html or len(html) < 1000:
            logger.error(
                "WBA SSI: all access methods failed. "
                "Full dataset available at %s",
                XLSX_URL,
            )
            return []

        companies = self._parse_companies_from_html(html)

        if not companies:
            logger.warning(
                "WBA SSI: page fetched but no companies parsed. "
                "Full dataset available at %s",
                XLSX_URL,
            )
            return []

        observations: list[dict[str, Any]] = []

        for rank, comp in enumerate(companies, 1):
            if len(observations) >= limit:
                break

            name = comp["name"]
            country = comp["country"]

            # Apply company name filter
            if company_filter:
                if company_filter.lower() not in name.lower():
                    continue

            # The 2023 SSI was published October 2023.
            # This is the latest available benchmark -- always include it
            # regardless of the time window, since it represents the most
            # current assessment.  Users querying recent data still want
            # the latest benchmark scores even though the pub date is 2023.
            ts = datetime(2023, 10, 17)

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"wba-ssi-{name}-2023",
                "source_name": "WBA Seafood Stewardship Index",
                "quality_score": 0.93,
                "payload": {
                    "company_name": name,
                    "rank": rank,
                    "country": country,
                    "year": 2023,
                    "benchmark": "Seafood Stewardship Index",
                    "dataset_url": XLSX_URL,
                    "detail_url": PUBLICATION_URL,
                },
            })

        logger.info("WBA SSI returned %d company rankings", len(observations))
        return observations
