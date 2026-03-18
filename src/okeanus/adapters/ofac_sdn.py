"""OFAC SDN adapter — US Treasury sanctions list with maritime identifiers.

The Specially Designated Nationals (SDN) list includes sanctioned vessels
identified by IMO number and MMSI. Updated daily. No auth required.

Source: https://sanctionslist.ofac.treas.gov/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# OFAC consolidated non-SDN JSON (includes vessels with IMO/MMSI)
SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV"
CONS_JSON_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONS_ENHANCED.CSV"


class OfacSdnAdapter(BaseAdapter):
    """Connector for OFAC SDN sanctions list (vessel identifiers)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "ofac_sdn"

    @property
    def source_url(self) -> str:
        return "https://sanctionslist.ofac.treas.gov/"

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
        """Fetch sanctioned entities from OFAC SDN list.

        Filters for vessel-related entries (those with vessel type,
        IMO numbers, or MMSI identifiers).

        Extra params:
            limit: Max records (default 100)
            search: Text search filter
        """
        limit = params.get("limit", 100)
        search = params.get("search", "").upper()

        try:
            resp = await self._request("GET", SDN_URL)
            text = resp.text
        except Exception as exc:
            logger.error("OFAC SDN fetch failed: %s", exc)
            return []

        observations: list[dict[str, Any]] = []
        lines = text.strip().split("\n")

        for line in lines:
            if len(observations) >= limit:
                break

            parts = line.split(",")
            if len(parts) < 12:
                continue

            # SDN CSV columns: uid, name, type, program, title, ...
            uid = parts[0].strip().strip('"')
            name = parts[1].strip().strip('"')
            entity_type = parts[2].strip().strip('"')
            program = parts[3].strip().strip('"')
            remarks = parts[11].strip().strip('"') if len(parts) > 11 else ""

            # Filter for vessel-related entries
            line_upper = line.upper()
            is_vessel = (
                entity_type == "-0- " or
                "VESSEL" in line_upper or
                "IMO" in line_upper or
                "MMSI" in line_upper or
                "SHIP" in line_upper
            )

            if not is_vessel:
                continue

            if search and search not in line_upper:
                continue

            # Extract IMO/MMSI from remarks if present
            imo = _extract_id(remarks, "IMO")
            mmsi = _extract_id(remarks, "MMSI")

            observations.append({
                "obs_type": "sanctions",
                "timestamp": datetime.now(timezone.utc),
                "geometry": None,
                "source_id": f"ofac-sdn-{uid}",
                "source_name": "OFAC SDN",
                "quality_score": 1.0,
                "payload": {
                    "uid": uid,
                    "name": name,
                    "entity_type": entity_type,
                    "program": program,
                    "remarks": remarks[:500],
                    "imo": imo,
                    "mmsi": mmsi,
                },
            })

        logger.info("OFAC SDN returned %d vessel-related entries", len(observations))
        return observations


def _extract_id(text: str, prefix: str) -> str | None:
    """Extract an identifier like IMO 1234567 from remarks text."""
    import re
    match = re.search(rf"{prefix}\s*[:#]?\s*(\d+)", text, re.IGNORECASE)
    return match.group(1) if match else None
