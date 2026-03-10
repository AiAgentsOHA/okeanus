"""Reef Life Survey (RLS) adapter — citizen science reef biodiversity surveys.

Standardised visual census surveys of reef biodiversity conducted by
trained recreational divers across 4,000+ sites worldwide. Data accessed
via the OBIS API with institutionCode=RLS filter. No auth required.

Data portal: https://reeflifesurvey.com/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.obis.org/v3"


class ReefLifeSurveyAdapter(BaseAdapter):
    """Connector for Reef Life Survey data via the OBIS API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "reef_life_survey"

    @property
    def source_url(self) -> str:
        return "https://reeflifesurvey.com/"

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
        """Fetch reef biodiversity survey observations.

        Extra params:
            taxon: scientific name filter
            size: Max results (default 500)
        """
        w, s, e, n = bbox
        geometry = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
        size = params.get("size", 500)

        api_params: dict[str, Any] = {
            "institutioncode": "RLS",
            "geometry": geometry,
            "startdate": time_start.strftime("%Y-%m-%d"),
            "enddate": time_end.strftime("%Y-%m-%d"),
            "size": size,
        }

        if taxon := params.get("taxon"):
            api_params["scientificname"] = taxon

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/occurrence", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("Reef Life Survey fetch failed: %s", exc)
            return []

        results = data.get("results", [])
        observations: list[dict[str, Any]] = []

        for rec in results:
            lon = rec.get("decimalLongitude")
            lat = rec.get("decimalLatitude")
            date_str = rec.get("eventDate") or rec.get("date_mid")
            if lon is None or lat is None or date_str is None:
                continue

            try:
                ts = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            aphia = rec.get("aphiaID") or rec.get("speciesid")

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"rls-{rec.get('id', '')}",
                "source_name": "Reef Life Survey",
                "quality_score": 0.85,
                "payload": {
                    "scientific_name": rec.get("scientificName", ""),
                    "aphia_id": int(aphia) if aphia else None,
                    "survey_site": rec.get("locality", ""),
                    "depth_m": rec.get("depth"),
                    "abundance": rec.get("individualCount"),
                    "survey_method": rec.get("samplingProtocol", ""),
                    "country": rec.get("country", ""),
                    "dataset_name": rec.get("dataset_id", ""),
                },
            })

        logger.info("Reef Life Survey returned %d observations", len(observations))
        return observations
