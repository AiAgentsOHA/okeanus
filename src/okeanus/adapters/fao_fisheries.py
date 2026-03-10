"""FAO Global Fisheries Statistics adapter — capture and aquaculture data.

FAO FIRMS (Fisheries and Resources Monitoring System) provides stock
status assessments and fisheries statistics. No auth required.

Data source: https://firms.fao.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://firms.fao.org/firms/stocks/search/json"


class FaoFisheriesAdapter(BaseAdapter):
    """Connector for FAO FIRMS fisheries stock data (no auth required).

    Returns stock assessments with species, area, and status information.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fao_fisheries"

    @property
    def source_url(self) -> str:
        return "https://firms.fao.org/"

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
        """Fetch fisheries stock assessments.

        Extra params:
            species: species common or scientific name
            area: FAO fishing area code (e.g. '27' for NE Atlantic)
            limit: Max records (default 200)
        """
        limit = params.get("limit", 200)
        w, s, e, n = bbox

        query_params: dict[str, Any] = {}
        if species := params.get("species"):
            query_params["species"] = species
        if area := params.get("area"):
            query_params["area"] = area

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("FAO Fisheries fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("stocks", data.get("results", []))
        if not isinstance(results, list):
            results = []

        observations: list[dict[str, Any]] = []
        lon_center = (w + e) / 2
        lat_center = (s + n) / 2

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            stock_id = rec.get("stock_id", rec.get("id", ""))
            year = rec.get("year") or rec.get("assessment_year")
            try:
                ts = datetime(int(year), 1, 1) if year else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            if ts < time_start or ts > time_end:
                continue

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon_center, lat_center]},
                "source_id": f"fao-stock-{stock_id}",
                "source_name": "FAO FIRMS",
                "quality_score": 0.9,
                "payload": {
                    "species": rec.get("species", rec.get("scientific_name", "")),
                    "common_name": rec.get("english_name", rec.get("common_name", "")),
                    "area": rec.get("area", rec.get("fao_area", "")),
                    "stock_status": rec.get("status", rec.get("stock_status", "")),
                    "exploitation_rate": rec.get("exploitation_rate"),
                    "biomass": rec.get("biomass"),
                    "management_body": rec.get("management_body", ""),
                    "year": year,
                    "catch_tonnes": rec.get("catch", rec.get("landings")),
                },
            })

        logger.info("FAO Fisheries returned %d stock records", len(observations))
        return observations
