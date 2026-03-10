"""OBIS-SEAMAP adapter — marine megafauna observations.

Marine mammal, sea turtle, and seabird observations from the
Spatial Ecological Analysis of Megavertebrate Populations database
at Duke University. No auth required.

Data portal: https://seamap.env.duke.edu/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.obis.org/v3"


class ObisSeamapAdapter(BaseAdapter):
    """Connector for OBIS-SEAMAP megafauna observations via the OBIS API.

    Queries the OBIS API filtered to OBIS-SEAMAP node datasets which contain
    marine mammal, sea turtle, and seabird sighting records.
    """

    # OBIS-SEAMAP node ID in the OBIS system
    SEAMAP_NODE_ID = "3f3b8f4a-5c6a-4a92-b48f-5f5e6e836f99"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "obis_seamap"

    @property
    def source_url(self) -> str:
        return "https://seamap.env.duke.edu/"

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
        """Fetch megafauna observations within bbox and time range.

        Extra params:
            taxon: scientific name filter
            group: 'mammals', 'turtles', 'seabirds'
        """
        w, s, e, n = bbox
        geometry = f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"
        size = params.get("limit", 500)

        api_params: dict[str, Any] = {
            "geometry": geometry,
            "startdate": time_start.strftime("%Y-%m-%d"),
            "enddate": time_end.strftime("%Y-%m-%d"),
            "size": size,
            "node_id": self.SEAMAP_NODE_ID,
        }

        # Filter by taxon group
        group = params.get("group", "")
        if group == "mammals":
            api_params["taxonid"] = "137087"  # Cetacea + Pinnipedia
        elif group == "turtles":
            api_params["taxonid"] = "136999"  # Testudines
        elif group == "seabirds":
            api_params["taxonid"] = "212"  # Aves

        if taxon := params.get("taxon"):
            api_params["scientificname"] = taxon

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/occurrence", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("OBIS-SEAMAP fetch failed: %s", exc)
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
                "source_id": f"seamap-{rec.get('id', rec.get('occurrenceID', ''))}",
                "source_name": "OBIS-SEAMAP",
                "aphia_id": int(aphia) if aphia else None,
                "quality_score": 0.85,
                "payload": {
                    "scientific_name": rec.get("scientificName", ""),
                    "class": rec.get("class", ""),
                    "order": rec.get("order", ""),
                    "family": rec.get("family", ""),
                    "species": rec.get("species", ""),
                    "individual_count": rec.get("individualCount"),
                    "basis_of_record": rec.get("basisOfRecord", ""),
                    "dataset_name": rec.get("dataset_id", ""),
                    "depth_m": rec.get("depth"),
                },
            })

        logger.info("OBIS-SEAMAP returned %d megafauna observations", len(observations))
        return observations
