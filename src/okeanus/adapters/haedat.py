"""HAEDAT adapter -- Harmful Algal Event Database.

Global database of harmful algal bloom (HAB) events maintained by
IOC-UNESCO. Data accessed through OBIS API. No auth required.

Data portal: https://haedat.iode.org/

Note: HAEDAT data is mostly historical (1980s-2020s). The last-365-day
window may not contain data. The adapter automatically widens the time
range when no recent data exists.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# HAEDAT data is published to OBIS as this dataset
OBIS_URL = "https://api.obis.org/v3/occurrence"
HAEDAT_DATASET_ID = "62ddad25-2a19-485d-9bae-7eb3a40a71c5"


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

    async def _query_obis(
        self,
        bbox: tuple[float, float, float, float],
        start_date: str,
        end_date: str,
        limit: int,
    ) -> list[dict]:
        """Issue a single OBIS query and return the results list."""
        w, s, e, n = bbox
        wkt = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
        api_params: dict[str, Any] = {
            "datasetid": HAEDAT_DATASET_ID,
            "geometry": wkt,
            "startdate": start_date,
            "enddate": end_date,
            "size": min(limit, 500),
        }
        resp = await self._request("GET", OBIS_URL, params=api_params)
        data = resp.json()
        return data.get("results", [])

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        limit = params.get("limit", 500)

        try:
            results = await self._query_obis(
                bbox,
                time_start.strftime("%Y-%m-%d"),
                time_end.strftime("%Y-%m-%d"),
                limit,
            )
        except Exception as exc:
            logger.error("HAEDAT/OBIS fetch failed: %s", exc)
            return []

        # HAEDAT data is historical -- most events predate last year.
        # If the requested time range returns nothing, widen to all time.
        if not results:
            logger.info("HAEDAT: no results in requested range, widening to all time")
            try:
                results = await self._query_obis(
                    bbox, "1900-01-01", time_end.strftime("%Y-%m-%d"), limit
                )
            except Exception as exc:
                logger.error("HAEDAT/OBIS widened fetch failed: %s", exc)
                return []

        observations: list[dict[str, Any]] = []

        for rec in results:
            lon = rec.get("decimalLongitude")
            lat = rec.get("decimalLatitude")
            if lon is None or lat is None:
                continue

            date_str = rec.get("eventDate", "")
            try:
                if "T" in str(date_str):
                    ts = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                elif len(str(date_str)) >= 10:
                    ts = datetime.fromisoformat(str(date_str)[:10] + "T00:00:00+00:00")
                elif len(str(date_str)) == 4:
                    ts = datetime(int(date_str), 1, 1)
                else:
                    continue
            except (ValueError, AttributeError):
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"haedat-{rec.get('occurrenceID', rec.get('id', len(observations)))}",
                "source_name": "HAEDAT",
                "quality_score": 0.85,
                "payload": {
                    "species": rec.get("scientificName", ""),
                    "country": rec.get("country", ""),
                    "locality": rec.get("locality", ""),
                    "dataset": rec.get("dataset_id", ""),
                    "basis_of_record": rec.get("basisOfRecord", ""),
                    "institution": rec.get("institutionCode", ""),
                },
            })

        logger.info("HAEDAT returned %d HAB events", len(observations))
        return observations
