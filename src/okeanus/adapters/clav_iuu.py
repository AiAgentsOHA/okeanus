"""CLAV IUU Vessel List adapter — Combined IUU Vessel List.

Aggregated IUU (Illegal, Unreported, Unregulated) fishing vessel lists
from all RFMOs, maintained by Trygg Mat Tracking (TMT). No auth required.

Data source: https://www.iuu-vessels.org/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.iuu-vessels.org/api"


class ClavIuuAdapter(BaseAdapter):
    """Connector for the Combined IUU Vessel List (no auth required).

    Returns vessels flagged for illegal fishing by RFMOs worldwide.
    No spatial coordinates per se — vessels are listed by flag state and RFMO.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "clav_iuu"

    @property
    def source_url(self) -> str:
        return "https://www.iuu-vessels.org/"

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
        """Fetch IUU-listed vessels.

        Since IUU listings don't have coordinates, results are returned
        with geometry at (0, 0). Use vessel identifiers (IMO, name) to
        cross-reference with AIS position data.

        Extra params:
            flag: Flag state filter (e.g. 'CHN', 'KOR')
            rfmo: RFMO filter (e.g. 'CCAMLR', 'ICCAT', 'WCPFC')
            vessel_name: Vessel name search
        """
        limit = params.get("limit", 200)

        api_params: dict[str, Any] = {
            "limit": limit,
            "format": "json",
        }
        if flag := params.get("flag"):
            api_params["flag"] = flag
        if rfmo := params.get("rfmo"):
            api_params["rfmo"] = rfmo
        if vessel_name := params.get("vessel_name"):
            api_params["name"] = vessel_name

        try:
            resp = await self._request(
                "GET", f"{BASE_URL}/vessels", params=api_params,
            )
            data = resp.json()
        except Exception as exc:
            logger.error("CLAV IUU fetch failed: %s", exc)
            return []

        results = data if isinstance(data, list) else data.get("vessels", data.get("results", []))
        observations: list[dict[str, Any]] = []

        for rec in results:
            if not isinstance(rec, dict):
                continue

            # IUU listings don't have coordinates
            date_str = rec.get("listingDate") or rec.get("date", "")
            try:
                if date_str and len(str(date_str)) >= 10:
                    ts = datetime.fromisoformat(str(date_str)[:10] + "T00:00:00+00:00")
                elif date_str and len(str(date_str)) == 4:
                    ts = datetime.fromisoformat(f"{date_str}-01-01T00:00:00+00:00")
                else:
                    ts = datetime.now()
            except (ValueError, AttributeError):
                ts = datetime.now()

            imo = rec.get("imo") or rec.get("IMO")
            mmsi = rec.get("mmsi") or rec.get("MMSI")

            observations.append({
                "obs_type": "vessel",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                "source_id": f"iuu-{rec.get('id', imo or rec.get('name', ''))}",
                "source_name": "CLAV IUU",
                "mmsi": int(mmsi) if mmsi else None,
                "quality_score": 0.95,
                "payload": {
                    "vessel_name": rec.get("name", rec.get("vesselName", "")),
                    "imo": imo,
                    "flag": rec.get("flag", rec.get("flagState", "")),
                    "rfmo": rec.get("rfmo", rec.get("listingOrganization", "")),
                    "call_sign": rec.get("callSign", ""),
                    "vessel_type": rec.get("vesselType", ""),
                    "listing_date": date_str,
                    "offence": rec.get("offence", rec.get("reason", "")),
                    "aliases": rec.get("aliases", []),
                    "previous_flags": rec.get("previousFlags", []),
                    "owner": rec.get("owner", ""),
                },
            })

        logger.info("CLAV IUU returned %d listed vessels", len(observations))
        return observations
