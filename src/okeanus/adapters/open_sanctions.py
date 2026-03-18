"""OpenSanctions adapter — sanctioned vessels and entities.

Provides lookup of sanctioned vessels by IMO number or name for
compliance screening and IUU vessel flagging.

The hosted API (api.opensanctions.org) now requires an API key.
This adapter uses the **free public bulk data exports** (JSON lines)
published at data.opensanctions.org, which require no authentication.

Bulk data docs: https://www.opensanctions.org/docs/bulk/
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Public bulk data — no auth.  The "vessels" topic is small (~200 KB gzip).
# Format: newline-delimited JSON (FtM entities).
BULK_URL = "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json"
VESSELS_URL = "https://data.opensanctions.org/datasets/latest/sanctions/targets.nested.json"


class OpenSanctionsAdapter(BaseAdapter):
    """Connector for OpenSanctions — uses free public bulk exports."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=120.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "opensanctions"

    @property
    def source_url(self) -> str:
        return "https://www.opensanctions.org/"

    @property
    def update_frequency(self) -> str:
        return "daily"

    async def search_vessel(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search sanctioned entities by name/IMO in the bulk export.

        Downloads the nested sanctions targets file (relatively small)
        and filters client-side.
        """
        try:
            resp = await self._request("GET", VESSELS_URL)
            text = resp.text
        except Exception as exc:
            logger.error("OpenSanctions bulk download failed: %s", exc)
            return []

        query_lower = query.lower()
        matches: list[dict[str, Any]] = []

        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Match against caption, properties.name, properties.imoNumber
            caption = (entity.get("caption") or "").lower()
            props = entity.get("properties") or {}
            names = [n.lower() for n in props.get("name", [])]
            imo_numbers = [str(i).lower() for i in props.get("imoNumber", [])]
            schema = (entity.get("schema") or "").lower()

            searchable = [caption] + names + imo_numbers
            if any(query_lower in s for s in searchable):
                matches.append(entity)
                if len(matches) >= limit:
                    break

        return matches

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Search for sanctioned vessels/entities.

        OpenSanctions is not a spatial API — pass ``query`` in params
        to search by vessel name, IMO number, or entity name.
        If no query is given, returns all Vessel-schema entities (up to limit).
        """
        query = params.get("query", "")
        limit = params.get("limit", 20)

        if not query:
            # Default: return vessel-schema entities
            query = ""

        try:
            resp = await self._request("GET", VESSELS_URL)
            text = resp.text
        except Exception as exc:
            logger.error("OpenSanctions bulk download failed: %s", exc)
            return []

        query_lower = query.lower()
        observations: list[dict[str, Any]] = []

        for line in text.splitlines():
            if len(observations) >= limit:
                break
            if not line.strip():
                continue
            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                continue

            props = entity.get("properties") or {}
            schema = entity.get("schema") or ""
            caption = entity.get("caption") or ""
            names = props.get("name", [])
            imo_numbers = props.get("imoNumber", [])
            mmsi_list = props.get("mmsi", [])
            flag_list = props.get("flag", [])

            # If query given, filter; otherwise return Vessel-schema only
            if query_lower:
                searchable = (
                    [caption.lower()]
                    + [n.lower() for n in names]
                    + [str(i).lower() for i in imo_numbers]
                )
                if not any(query_lower in s for s in searchable):
                    continue
            else:
                if schema != "Vessel":
                    continue

            observations.append({
                "obs_type": "vessel",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"sanctions-{entity.get('id', '')}",
                "source_name": "OpenSanctions",
                "mmsi": int(mmsi_list[0]) if mmsi_list else None,
                "quality_score": 1.0,
                "payload": {
                    "entity_id": entity.get("id", ""),
                    "names": names,
                    "imo_numbers": imo_numbers,
                    "flags": flag_list,
                    "sanctions_datasets": entity.get("datasets", []),
                    "schema": schema,
                    "caption": caption,
                    "sanctioned": True,
                },
            })

        logger.info("OpenSanctions returned %d entities", len(observations))
        return observations
