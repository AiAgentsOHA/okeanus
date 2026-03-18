"""CPR Survey (Continuous Plankton Recorder) adapter.

The CPR Survey has collected plankton samples from commercial ships
since 1931 -- the longest-running marine biological survey in the world.
Managed by the Marine Biological Association (MBA).

The DASSH ERDDAP server (www.dassh.ac.uk/erddap) went offline in 2025.
CPR zooplankton data is now accessed via OBIS (Ocean Biodiversity
Information System) which hosts the full dataset.

Data source: https://www.cprsurvey.org/
OBIS dataset: https://obis.org/dataset/10134dbd-457e-4a97-9a89-b4e9f81482ca
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# OBIS REST API -- CPR Survey zooplankton dataset
OBIS_URL = "https://api.obis.org/v3/occurrence"
CPR_DATASET_ID = "10134dbd-457e-4a97-9a89-b4e9f81482ca"


class CprSurveyAdapter(BaseAdapter):
    """Connector for CPR Survey plankton data via OBIS (no auth required).

    Returns plankton occurrence observations from the Continuous
    Plankton Recorder survey since 1931.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "cpr_survey"

    @property
    def source_url(self) -> str:
        return "https://www.cprsurvey.org/"

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
        """Fetch CPR Survey plankton data from OBIS.

        Extra params:
            taxon: scientific name filter (e.g. 'Calanus finmarchicus')
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        taxon = params.get("taxon")

        # Default to North Atlantic where CPR has best coverage
        if (e - w) > 100 or (n - s) > 80:
            w, s, e, n = -60.0, 40.0, 10.0, 65.0

        # Build WKT POLYGON for OBIS geometry filter
        wkt = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"

        # CPR data in OBIS has a multi-year publication lag (latest
        # records are often 3-8 years old).  We first try with the
        # requested time window; if empty, we retry without the date
        # filter so the adapter still returns data.
        api_params: dict[str, Any] = {
            "datasetid": CPR_DATASET_ID,
            "geometry": wkt,
            "size": min(limit, 500),
        }
        if taxon:
            api_params["scientificname"] = taxon

        # First attempt: with date filter
        dated_params = {
            **api_params,
            "startdate": time_start.strftime("%Y-%m-%d"),
            "enddate": time_end.strftime("%Y-%m-%d"),
        }
        try:
            resp = await self._request("GET", OBIS_URL, params=dated_params)
            data = resp.json()
        except Exception as exc:
            logger.error("CPR Survey (OBIS) fetch failed: %s", exc)
            return []

        results = data.get("results", [])

        if not results:
            # Retry without date filter -- return most recent available
            logger.info("CPR Survey: no data in requested window, fetching latest available")
            try:
                resp = await self._request("GET", OBIS_URL, params=api_params)
                data = resp.json()
            except Exception as exc:
                logger.error("CPR Survey (OBIS) fallback fetch failed: %s", exc)
                return []
            results = data.get("results", [])
        observations: list[dict[str, Any]] = []

        for rec in results:
            if len(observations) >= limit:
                break

            if not isinstance(rec, dict):
                continue

            lat = rec.get("decimalLatitude")
            lon = rec.get("decimalLongitude")
            if lat is None or lon is None:
                continue

            try:
                lat = float(lat)
                lon = float(lon)
            except (ValueError, TypeError):
                continue

            # Parse event date — OBIS may return eventDate as a string,
            # or separate year/month/day integer fields.
            ts: datetime = time_start
            date_str = rec.get("eventDate") or ""
            year_val = rec.get("year")
            if date_str:
                try:
                    ts = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    try:
                        ts = datetime.strptime(
                            str(date_str)[:10], "%Y-%m-%d"
                        ).replace(tzinfo=timezone.utc)
                    except (ValueError, TypeError):
                        ts = time_start
            elif year_val:
                try:
                    y = int(year_val)
                    m = int(rec.get("month") or 1)
                    d = int(rec.get("day") or 1)
                    ts = datetime(y, m, d, tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    ts = time_start

            sci_name = rec.get("scientificName", "")
            occ_id = rec.get("occurrenceID", rec.get("id", ""))

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"cpr-{occ_id}",
                "source_name": "CPR Survey",
                "quality_score": 0.9,
                "payload": {
                    "taxon": sci_name,
                    "phylum": rec.get("phylum", ""),
                    "class": rec.get("class", ""),
                    "order": rec.get("order", ""),
                    "family": rec.get("family", ""),
                    "genus": rec.get("genus", ""),
                    "depth_m": rec.get("depth"),
                    "basis_of_record": rec.get("basisOfRecord", ""),
                    "dataset": "CPR Survey (via OBIS)",
                    "survey": "Continuous Plankton Recorder",
                },
            })

        logger.info("CPR Survey returned %d observations", len(observations))
        return observations
