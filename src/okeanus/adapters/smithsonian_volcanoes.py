"""Smithsonian Global Volcanism Program adapter — submarine volcanoes.

The GVP maintains the authoritative database of ~3,000 active volcanoes
including submarine and island-arc volcanoes. REST/download access via
the Holocene Volcano List. No auth required.

Data source: https://volcano.si.edu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

WFS_URL = (
    "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/ows"
)


class SmithsonianVolcanoesAdapter(BaseAdapter):
    """Connector for Smithsonian GVP volcano database (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "smithsonian_volcanoes"

    @property
    def source_url(self) -> str:
        return "https://volcano.si.edu/"

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
        """Fetch volcano data within bbox.

        Extra params:
            submarine_only: if True, only submarine volcanoes (default True)
            limit: max records (default 500)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 500)
        submarine_only = params.get("submarine_only", False)

        # Use GeoServer WFS endpoint for GVP Holocene Volcanoes
        cql_filters: list[str] = []
        cql_filters.append(f"BBOX(GeoLocation,{w},{s},{e},{n})")
        if submarine_only:
            cql_filters.append("Primary_Volcano_Type LIKE '%Submarine%'")

        api_params: dict[str, Any] = {
            "service": "WFS",
            "version": "1.0.0",
            "request": "GetFeature",
            "typeName": "GVP-VOTW:Smithsonian_VOTW_Holocene_Volcanoes",
            "outputFormat": "application/json",
            "maxFeatures": limit,
            "CQL_FILTER": " AND ".join(cql_filters),
        }

        try:
            resp = await self._request("GET", WFS_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Smithsonian GVP fetch failed: %s", exc)
            # Retry without submarine filter in case it's too restrictive
            if submarine_only:
                api_params["CQL_FILTER"] = f"BBOX(GeoLocation,{w},{s},{e},{n})"
                try:
                    resp = await self._request("GET", WFS_URL, params=api_params)
                    data = resp.json()
                except Exception:
                    return []
            else:
                return []

        features = data.get("features", [])
        observations: list[dict[str, Any]] = []

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})

            coords = geom.get("coordinates", [])
            if len(coords) >= 2:
                lon, lat = float(coords[0]), float(coords[1])
            else:
                continue

            last_eruption = props.get("Last_Eruption_Year")
            try:
                if last_eruption and str(last_eruption).strip() not in ("", "Unknown"):
                    ts = datetime(int(last_eruption), 1, 1)
                else:
                    ts = time_start
            except (ValueError, TypeError):
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"gvp-{props.get('Volcano_Number', '')}",
                "source_name": "Smithsonian GVP",
                "quality_score": 0.95,
                "payload": {
                    "volcano_name": props.get("Volcano_Name", ""),
                    "volcano_number": props.get("Volcano_Number"),
                    "primary_type": props.get("Primary_Volcano_Type", ""),
                    "country": props.get("Country", ""),
                    "region": props.get("Region", ""),
                    "subregion": props.get("Subregion", ""),
                    "summit_elevation_m": props.get("Elevation"),
                    "last_eruption_year": last_eruption,
                    "tectonic_setting": props.get("Tectonic_Setting", ""),
                    "dominant_rock_type": props.get("Major_Rock_Type", ""),
                },
            })

        logger.info("Smithsonian GVP returned %d volcanoes", len(observations))
        return observations
