"""Tokyo MOU Port State Control adapter.

Tokyo MOU coordinates port state control inspections across the
Asia-Pacific region — 21 member authorities inspecting ~30,000
vessels annually.

Data scraped from the APCIS public detention list via Playwright.
No auth required.

Data source: https://www.tokyo-mou.org/
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

APCIS_URL = "https://apcis.tmou.org/isss/public_apcis.php?Mode=DetList"


class TokyoMouPscAdapter(BaseAdapter):
    """Connector for Tokyo MOU Asia-Pacific PSC detentions via APCIS.

    Uses Playwright to interact with the APCIS detention list form
    and extract table data.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=0.5, timeout=90.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "tokyo_mou_psc"

    @property
    def source_url(self) -> str:
        return "https://www.tokyo-mou.org/"

    @property
    def update_frequency(self) -> str:
        return "monthly"

    def _scrape_sync(
        self, year: int, limit: int,
    ) -> list[dict[str, Any]]:
        """Synchronous Playwright scrape — runs in executor."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("playwright not installed: pip install playwright")
            return []

        records: list[dict[str, Any]] = []
        tag_re = re.compile(r"<[^>]+>")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(APCIS_URL, timeout=30000)
                page.wait_for_timeout(2000)

                # Select year and submit
                page.select_option('select[name="yearSel"]', str(year))
                apply_btn = page.query_selector('input[value="Apply"]')
                if apply_btn:
                    apply_btn.click()
                page.wait_for_timeout(5000)

                # Parse table rows
                rows = page.query_selector_all("table tr")
                header_found = False
                col_map: dict[int, str] = {}

                for row in rows:
                    cells = row.query_selector_all("td")
                    if not cells:
                        continue
                    texts = [c.inner_text().strip() for c in cells]

                    # Detect header row
                    if not header_found and "IMO No." in texts:
                        for i, t in enumerate(texts):
                            col_map[i] = t
                        header_found = True
                        continue

                    if not header_found:
                        continue

                    # Skip rows that are clearly not data
                    if len(texts) < 5 or not texts[0].isdigit():
                        continue

                    if len(records) >= limit:
                        break

                    records.append({
                        "row_num": texts[0] if len(texts) > 0 else "",
                        "imo": texts[1] if len(texts) > 1 else "",
                        "ship_name": texts[2] if len(texts) > 2 else "",
                        "flag": texts[3] if len(texts) > 3 else "",
                        "year_of_build": texts[4] if len(texts) > 4 else "",
                        "gross_tonnage": texts[5] if len(texts) > 5 else "",
                        "ship_type": texts[6] if len(texts) > 6 else "",
                        "class_society": texts[7] if len(texts) > 7 else "",
                        "authority": texts[8] if len(texts) > 8 else "",
                        "port": texts[9] if len(texts) > 9 else "",
                        "detention_date": texts[10] if len(texts) > 10 else "",
                    })

                browser.close()
        except Exception as exc:
            logger.error("Tokyo MOU Playwright scrape failed: %s", exc)

        return records

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch Tokyo MOU detention data via APCIS.

        Extra params:
            year: specific year to query (default: time_end year)
            limit: max records (default 200)
        """
        limit = params.get("limit", 200)
        year = params.get("year", time_end.year)

        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(
            None, self._scrape_sync, year, limit,
        )

        observations: list[dict[str, Any]] = []
        for rec in records:
            imo = rec.get("imo", "")
            det_date = rec.get("detention_date", "")

            observations.append({
                "obs_type": "governance",
                "timestamp": datetime(year, 1, 1),
                "geometry": {"type": "Point", "coordinates": [130.0, 25.0]},
                "source_id": f"tokyomou-{imo}-{det_date}",
                "source_name": "Tokyo MOU PSC",
                "quality_score": 0.85,
                "payload": {
                    "vessel_name": rec.get("ship_name", ""),
                    "imo_number": imo,
                    "flag_state": rec.get("flag", ""),
                    "ship_type": rec.get("ship_type", ""),
                    "gross_tonnage": rec.get("gross_tonnage", ""),
                    "year_of_build": rec.get("year_of_build", ""),
                    "class_society": rec.get("class_society", ""),
                    "authority": rec.get("authority", ""),
                    "port": rec.get("port", ""),
                    "detention_date": det_date,
                },
            })

        logger.info("Tokyo MOU returned %d detention records", len(observations))
        return observations
