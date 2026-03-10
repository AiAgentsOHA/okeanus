"""Thetis MRV adapter — EU ship emissions monitoring.

EU MRV (Monitoring, Reporting, Verification) regulation data for ship
CO2 emissions from EMSA's THETIS-MRV system. Covers all ships >5000 GT
calling at EU/EEA ports. No auth required for public aggregate data.

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
    """Connector for THETIS-MRV ship emissions data (no auth required).

    Returns aggregated ship emission reports by year.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

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
        """
        year = params.get("year", time_end.year - 1)
        ship_type = params.get("ship_type")
        limit = params.get("limit", 200)

        query_params: dict[str, Any] = {"year": year}
        if ship_type:
            query_params["shipType"] = ship_type

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Thetis MRV fetch failed: %s", exc)
            return []

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
