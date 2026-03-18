"""IUU Fishing Index adapter — country compliance rankings.

IUU (Illegal, Unreported and Unregulated) fishing risk scores
for coastal, flag, port, and market states based on 40 indicators.

Data: CSV download from iuufishingindex.net (ZIP archive).
No auth required.
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

ZIP_URL = "https://iuufishingindex.net/downloads/iuu_fishing_index_2025-data_and_disclaimer.zip"
CSV_FILENAME = "iuu_fishing_index_2019-2025_indicator_scores.xlsx - 2019-2025 indicator scores.csv"


class IuuIndexAdapter(BaseAdapter):
    """Connector for IUU Fishing Index — country compliance (no auth).

    Downloads the indicator-level CSV from the IUU Fishing Index website
    and computes average scores per country for the requested years.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "iuu_index"

    @property
    def source_url(self) -> str:
        return "https://iuufishingindex.net/"

    @property
    def update_frequency(self) -> str:
        return "yearly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch IUU Fishing Index country rankings.

        Downloads the ZIP with indicator-level CSV and computes average
        scores per country for the requested time range.

        Extra params:
            country: country name filter
            limit: max records (default: 200)
        """
        country_filter = params.get("country")
        limit = params.get("limit", 200)

        # Download ZIP
        try:
            resp = await self._request("GET", ZIP_URL)
            zip_bytes = resp.content
        except Exception as exc:
            logger.error("IUU Index ZIP download failed: %s", exc)
            return []

        # Extract CSV from ZIP
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
            csv_data = zf.read(CSV_FILENAME).decode("utf-8")
        except Exception as exc:
            logger.error("IUU Index ZIP extraction failed: %s", exc)
            return []

        # Parse CSV: columns are Indicator ID, Indicator name, Country,
        # Region, Ocean, Resp, Type, Year, Score
        year_start = time_start.year
        year_end = time_end.year
        # Available years: 2019, 2021, 2023, 2025
        valid_years = {str(y) for y in range(year_start, year_end + 1)}

        # Aggregate scores per (country, year)
        country_data: dict[tuple[str, str], dict[str, Any]] = {}

        reader = csv.DictReader(io.StringIO(csv_data))
        for row in reader:
            yr = row.get("Year", "")
            if yr not in valid_years:
                continue

            cname = row.get("Country", "")
            if country_filter and country_filter.lower() not in cname.lower():
                continue

            key = (cname, yr)
            if key not in country_data:
                country_data[key] = {
                    "country": cname,
                    "region": row.get("Region", ""),
                    "ocean": row.get("Ocean", ""),
                    "year": yr,
                    "scores": [],
                    "vulnerability_scores": [],
                    "prevalence_scores": [],
                    "response_scores": [],
                }

            try:
                score = float(row.get("Score", ""))
            except (ValueError, TypeError):
                continue

            country_data[key]["scores"].append(score)
            score_type = row.get("Type", "").lower()
            if "vulnerability" in score_type:
                country_data[key]["vulnerability_scores"].append(score)
            elif "prevalence" in score_type:
                country_data[key]["prevalence_scores"].append(score)
            elif "response" in score_type:
                country_data[key]["response_scores"].append(score)

        # Build observations
        observations: list[dict[str, Any]] = []

        for (cname, yr), info in country_data.items():
            scores = info["scores"]
            if not scores:
                continue

            avg_score = sum(scores) / len(scores)
            vuln = info["vulnerability_scores"]
            prev = info["prevalence_scores"]
            resp_scores = info["response_scores"]

            try:
                ts = datetime(int(yr), 1, 1)
            except (ValueError, TypeError):
                continue

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"iuu-idx-{cname.replace(' ', '_')}-{yr}",
                "source_name": "IUU Fishing Index",
                "quality_score": 0.90,
                "payload": {
                    "country_name": cname,
                    "region": info["region"],
                    "ocean": info["ocean"],
                    "overall_score": round(avg_score, 2),
                    "n_indicators": len(scores),
                    "vulnerability": round(sum(vuln) / len(vuln), 2) if vuln else None,
                    "prevalence": round(sum(prev) / len(prev), 2) if prev else None,
                    "response": round(sum(resp_scores) / len(resp_scores), 2) if resp_scores else None,
                    "year": int(yr),
                },
            })

            if len(observations) >= limit:
                break

        logger.info("IUU Index returned %d country scores", len(observations))
        return observations
