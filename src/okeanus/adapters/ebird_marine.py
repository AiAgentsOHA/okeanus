"""eBird marine/seabird observations adapter.

eBird (Cornell Lab of Ornithology) provides the world's largest
biodiversity citizen science dataset. This adapter targets marine
and seabird species observations near coastlines and at sea.

API: REST at api.ebird.org/v2. Requires free API key.
Get key at: https://ebird.org/api/keygen

Data source: https://ebird.org/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ebird.org/v2"

# Marine/seabird species codes for filtering
MARINE_SPECIES = {
    "albatross", "petrel", "shearwater", "storm-petrel", "gannet",
    "booby", "cormorant", "frigatebird", "pelican", "gull", "tern",
    "skua", "jaeger", "auk", "murre", "puffin", "guillemot",
    "razorbill", "penguin", "tropicbird", "phalarope", "skimmer",
    "noddy", "fulmar", "prion", "diving-petrel", "kittiwake",
}


class EbirdMarineAdapter(BaseAdapter):
    """Connector for eBird marine/seabird observations (requires free API key).

    Set EBIRD_API_KEY env variable. Get free key at:
    https://ebird.org/api/keygen
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)
        self._api_key = os.environ.get("EBIRD_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "ebird_marine"

    @property
    def source_url(self) -> str:
        return "https://ebird.org/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch marine bird observations within bbox.

        Extra params:
            species_code: eBird species code (e.g. 'bkbgul' for Black-backed Gull)
            marine_only: if True, filter to marine species (default True)
            back: days back from today (default 14, max 30)
            limit: max records (default 500)
        """
        if not self._api_key:
            logger.warning("EBIRD_API_KEY not set — get free key at https://ebird.org/api/keygen")
            return []

        w, s, e, n = bbox
        marine_only = params.get("marine_only", True)
        species_code = params.get("species_code")
        back = params.get("back", 14)
        limit = params.get("limit", 500)

        # Clamp bbox to reasonable size
        if (e - w) > 20 or (n - s) > 20:
            center_lon = (w + e) / 2
            center_lat = (s + n) / 2
            w = center_lon - 5
            e = center_lon + 5
            s = center_lat - 5
            n = center_lat + 5

        headers = {"X-eBirdApiToken": self._api_key}

        if species_code:
            url = f"{BASE_URL}/data/obs/geo/recent/{species_code}"
        else:
            url = f"{BASE_URL}/data/obs/geo/recent"

        api_params: dict[str, Any] = {
            "lat": (s + n) / 2,
            "lng": (w + e) / 2,
            "dist": min(int(((e - w) + (n - s)) / 2 * 111 / 2), 50),  # km, max 50
            "back": min(back, 30),
            "maxResults": limit,
            "includeProvisional": "true",
        }

        try:
            resp = await self._request("GET", url, params=api_params, headers=headers)
            data = resp.json()
        except Exception as exc:
            logger.error("eBird API fetch failed: %s", exc)
            return []

        if not isinstance(data, list):
            return []

        observations: list[dict[str, Any]] = []

        for obs in data:
            if not isinstance(obs, dict):
                continue

            com_name = (obs.get("comName") or "").lower()
            sci_name = (obs.get("sciName") or "").lower()

            # Filter to marine species if requested
            if marine_only and not species_code:
                is_marine = any(
                    kw in com_name or kw in sci_name
                    for kw in MARINE_SPECIES
                )
                if not is_marine:
                    continue

            lat = obs.get("lat")
            lon = obs.get("lng")
            if lat is None or lon is None:
                continue

            date_str = obs.get("obsDt", "")
            try:
                ts = datetime.fromisoformat(date_str) if date_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [float(lon), float(lat)]},
                "source_id": f"ebird-{obs.get('subId', '')}-{obs.get('speciesCode', '')}",
                "source_name": "eBird",
                "quality_score": 0.85 if obs.get("obsValid") else 0.7,
                "payload": {
                    "species_code": obs.get("speciesCode", ""),
                    "common_name": obs.get("comName", ""),
                    "scientific_name": obs.get("sciName", ""),
                    "count": obs.get("howMany"),
                    "location_name": obs.get("locName", ""),
                    "location_id": obs.get("locId", ""),
                    "observation_date": date_str,
                    "validated": obs.get("obsValid", False),
                    "reviewed": obs.get("obsReviewed", False),
                },
            })

        logger.info("eBird returned %d marine observations", len(observations))
        return observations
