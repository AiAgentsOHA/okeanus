"""BarentsWatch adapter — Norwegian aquaculture site data.

BarentsWatch fishhealth API requires OAuth2 client credentials.
This adapter falls back to the Norwegian Directorate of Fisheries
(Fiskeridirektoratet) open API at api.fiskeridir.no which provides
aquaculture site data (localities, species, capacity, licenses)
without authentication.

Data source (primary):  https://api.fiskeridir.no/pub-aqua/api/v1/sites
Data source (original): https://www.barentswatch.no/bwapi/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# BarentsWatch API requires OAuth2 — all endpoints return 401 without token.
BW_API = "https://www.barentswatch.no/bwapi"

# Fiskeridirektoratet open API — no auth required, rich aquaculture data.
FISKERIDIR_API = "https://api.fiskeridir.no/pub-aqua/api/v1"


class BarentswatchAdapter(BaseAdapter):
    """Connector for Norwegian aquaculture site data.

    Primary: Fiskeridirektoratet open API (no auth).
    Fallback: BarentsWatch fishhealth API (requires OAuth2 — will fail
    without credentials configured in environment).
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, timeout=60.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "barentswatch"

    @property
    def source_url(self) -> str:
        return "https://api.fiskeridir.no/pub-aqua/api/v1/sites"

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch Norwegian aquaculture site data.

        Uses the Fiskeridirektoratet open API which returns site
        information including coordinates, species, capacity, licenses,
        and municipality/county placement data.

        Extra params:
            limit: max records (default 500)
            page_size: API page size (default 100)
        """
        limit = params.get("limit", 500)
        page_size = min(params.get("page_size", 100), 100)

        w, s, e, n = bbox

        # Default to Norwegian coast if global bbox
        if (e - w) > 60 or (n - s) > 40:
            w, s, e, n = 4.0, 58.0, 31.0, 71.0

        observations: list[dict[str, Any]] = []
        page = 0
        max_pages = (limit // page_size) + 1

        while len(observations) < limit and page < max_pages:
            url = f"{FISKERIDIR_API}/sites"
            query_params: dict[str, Any] = {
                "page": page,
                "size": page_size,
            }

            try:
                resp = await self._request("GET", url, params=query_params)
                data = resp.json()
            except Exception as exc:
                if page == 0:
                    logger.error(
                        "Fiskeridirektoratet API failed: %s. "
                        "BarentsWatch fishhealth API requires OAuth2 client "
                        "credentials — register at "
                        "https://developer.barentswatch.no/",
                        exc,
                    )
                break

            records = data if isinstance(data, list) else data.get("data", [])
            if not isinstance(records, list) or not records:
                break

            for rec in records:
                if len(observations) >= limit:
                    break

                if not isinstance(rec, dict):
                    continue

                lat = rec.get("latitude")
                lon = rec.get("longitude")
                if lat is None or lon is None:
                    continue

                try:
                    lat_f = float(lat)
                    lon_f = float(lon)
                except (ValueError, TypeError):
                    continue

                # Check bbox
                if not (w <= lon_f <= e and s <= lat_f <= n):
                    continue

                site_nr = rec.get("siteNr", "")
                name = rec.get("name", "")
                placement = rec.get("placement", {}) or {}
                species_types = rec.get("speciesTypes", []) or []
                capacity = rec.get("capacity")
                capacity_unit = rec.get("capacityUnitType", "")
                water_type = rec.get("waterType", "")
                placement_type = rec.get("placementType", "")

                observations.append({
                    "obs_type": "biological",
                    "timestamp": time_start,
                    "geometry": {"type": "Point", "coordinates": [lon_f, lat_f]},
                    "source_id": f"bw-{site_nr}",
                    "source_name": "Fiskeridirektoratet / BarentsWatch",
                    "quality_score": 0.9,
                    "payload": {
                        "site_name": name,
                        "site_number": str(site_nr),
                        "municipality": placement.get("municipalityName", ""),
                        "municipality_code": placement.get("municipalityCode", ""),
                        "county": placement.get("countyName", ""),
                        "county_code": placement.get("countyCode", ""),
                        "production_area": placement.get("prodAreaName", ""),
                        "production_area_status": placement.get("prodAreaStatus", ""),
                        "species_types": species_types,
                        "capacity": capacity,
                        "capacity_unit": capacity_unit,
                        "water_type": water_type,
                        "placement_type": placement_type,
                        "has_commercial_activity": rec.get("hasCommercialActivity", False),
                        "first_clearance_date": rec.get("firstClearanceTime", ""),
                    },
                })

            # If we got fewer records than page_size, no more pages
            if len(records) < page_size:
                break
            page += 1

        logger.info("Fiskeridirektoratet returned %d aquaculture sites", len(observations))
        return observations
