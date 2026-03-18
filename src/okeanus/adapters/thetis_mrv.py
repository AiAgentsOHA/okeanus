"""Thetis MRV adapter — EU ship emissions monitoring.

EU MRV (Monitoring, Reporting, Verification) regulation data for ship
CO2 emissions from EMSA's THETIS-MRV system. Covers all ships >5000 GT
calling at EU/EEA ports.

WAF STATUS (verified 2026-03-18, re-verified same session):
  The EMSA API at mrv.emsa.europa.eu is behind an F5 BIG-IP WAF.
  All programmatic requests are rejected:
    - GET with ANY sortColumn value -> 400 "Please insert pagination sort column"
      (WAF rejection, not a real parameter error — tested shipName, ship_name,
      SHIP_NAME, imoNumber, imo_number, IMO_NUMBER, totalCo2Emissions)
    - POST /search variant -> 404
    - /csv and /export endpoints -> 404
    - Playwright headless -> same 400 from WAF
    - Scrapling StealthyFetcher -> untested (JS-rendered SPA)

  The 400 response includes F5 WAF cookies (P_THETIS_MRV, TS013a928b)
  confirming the WAF intercept.

  Alternative sources investigated (all dead ends):
    - EU Open Data Portal (data.europa.eu/data/datasets/co2-emissions-data):
      only links back to mrv.emsa.europa.eu, no direct download
    - portal.emsa.europa.eu REST endpoints: all 404
    - EEA Datahub: has EU ETS data viewer but no ship-level MRV download
    - climate.ec.europa.eu: policy docs only, no raw data files

  Data IS publicly available via browser at:
    https://mrv.emsa.europa.eu/#/public/emission-report
  The browser can download CSV/XLSX from the search results page,
  but these downloads require solving a reCAPTCHA challenge.

  Data covers reporting years 2018-2023 (as of 2026).

  STATUS: BLOCKED — no programmatic access path exists. Monitor for EMSA
  API changes or consider manual CSV upload workflow.

Data source: https://mrv.emsa.europa.eu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://mrv.emsa.europa.eu/api/public-emission-report"


class ThetisMrvAdapter(BaseAdapter):
    """Connector for THETIS-MRV ship emissions data.

    Returns aggregated ship emission reports by year.

    WARNING: API is WAF-protected (F5 BIG-IP + reCAPTCHA). All
    programmatic requests are rejected with a 400 error. This adapter
    makes a single attempt per call to detect if EMSA restores access,
    but will return empty under current conditions.
    """

    def __init__(self, **kwargs: Any) -> None:
        # Only 1 retry -- WAF rejection is deterministic, retries waste time
        super().__init__(requests_per_second=1.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "thetis_mrv"

    @property
    def source_url(self) -> str:
        return "https://mrv.emsa.europa.eu/"

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
        """Fetch ship emissions data from THETIS-MRV.

        Extra params:
            year: reporting year (default: time_end.year - 1)
            ship_type: filter by ship type
            limit: Max records (default 200)

        NOTE: Currently returns empty due to F5 WAF protection.
        The API is probed once to detect if EMSA has restored access.
        Data is available via browser at:
        https://mrv.emsa.europa.eu/#/public/emission-report
        """
        year = params.get("year", time_end.year - 1)
        ship_type = params.get("ship_type")
        limit = params.get("limit", 200)

        # Single probe attempt -- WAF rejection is deterministic so
        # cycling through multiple years just wastes time and generates
        # noisy retry logs.
        query_params: dict[str, Any] = {
            "year": year,
            "sortColumn": "shipName",
            "sortDirection": "ASC",
            "page": 0,
            "size": min(limit, 50),
        }
        if ship_type:
            query_params["shipType"] = ship_type

        data = None
        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            if resp.status_code < 400:
                data = resp.json()
        except Exception:
            pass

        if data is None:
            logger.warning(
                "Thetis MRV API is WAF-protected (F5 BIG-IP + reCAPTCHA). "
                "Programmatic access is blocked. Data available via browser: "
                "https://mrv.emsa.europa.eu/#/public/emission-report"
            )
            return []

        # If we get here, EMSA has restored API access
        logger.info("Thetis MRV API access restored -- processing results")

        results = data if isinstance(data, list) else data.get("data", data.get("results", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []
        w, s, e, n = bbox
        lon_center = (w + e) / 2
        lat_center = (s + n) / 2

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            imo = rec.get("imo_number", rec.get("imoNumber", ""))

            observations.append({
                "obs_type": "regulatory",
                "timestamp": datetime(int(year), 12, 31),
                "geometry": {"type": "Point", "coordinates": [lon_center, lat_center]},
                "source_id": f"thetis-mrv-{imo}-{year}",
                "source_name": "Thetis MRV",
                "quality_score": 0.9,
                "payload": {
                    "imo_number": imo,
                    "ship_name": rec.get("ship_name", rec.get("shipName", "")),
                    "ship_type": rec.get("ship_type", rec.get("shipType", "")),
                    "flag_state": rec.get("flag_state", rec.get("flagState", "")),
                    "technical_efficiency": rec.get("technical_efficiency"),
                    "total_co2_tonnes": rec.get("total_co2", rec.get("totalCo2")),
                    "fuel_consumption_tonnes": rec.get("fuel_consumption", rec.get("totalFuelConsumption")),
                    "distance_nm": rec.get("distance", rec.get("totalDistanceTravelled")),
                    "transport_work": rec.get("transport_work"),
                    "avg_speed_knots": rec.get("average_speed"),
                    "reporting_period": str(year),
                },
            })

        logger.info("Thetis MRV returned %d ship emission records", len(observations))
        return observations
