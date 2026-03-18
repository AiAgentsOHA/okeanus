"""Paris MOU Port State Control adapter.

Paris MOU publishes vessel inspection results, detentions, and
deficiency data for ships inspected in European/North Atlantic ports.
~14,000 inspections per year.

Data accessed via EMSA's public detention REST API (discovered behind
the Paris MOU web portal). No auth required.

Data source: https://www.parismou.org/
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# EMSA public detention API (serves Paris MOU current detentions)
DETENTIONS_API = "https://portal.emsa.europa.eu/o/portlet-public/rest/detention/getCurrentDetentions.json"


class ParisMouPscAdapter(BaseAdapter):
    """Connector for Paris MOU port state control detentions via EMSA API.

    EMSA's API is intermittently slow or returns 500. This adapter uses
    tight connect/read timeouts and an outer asyncio deadline to fail
    fast rather than burn 90s on a hung server.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=1.0, timeout=15.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "paris_mou_psc"

    @property
    def source_url(self) -> str:
        return "https://www.parismou.org/"

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
        """Fetch Paris MOU current detention data from EMSA API.

        Extra params:
            limit: max records (default 50)
        """
        limit = params.get("limit", 50)

        # Use tight per-phase timeouts and an outer 40s deadline
        timeout_cfg = httpx.Timeout(connect=8.0, read=20.0, write=5.0, pool=5.0)
        try:
            async with httpx.AsyncClient(
                timeout=timeout_cfg, follow_redirects=True
            ) as client:
                resp = await asyncio.wait_for(
                    client.get(
                        DETENTIONS_API,
                        params={"page": 1, "start": 0, "limit": limit},
                    ),
                    timeout=40.0,
                )
                resp.raise_for_status()
                data = resp.json()
        except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
            logger.error("Paris MOU EMSA API timed out: %s", exc)
            return []
        except Exception as exc:
            logger.error("Paris MOU EMSA API failed: %s", exc)
            return []

        results = data.get("results", []) if isinstance(data, dict) else data
        if not isinstance(results, list):
            return []

        observations: list[dict[str, Any]] = []
        w, s, e, n = bbox

        for rec in results:
            if not isinstance(rec, dict):
                continue

            imo = str(rec.get("imoNumber", ""))
            ship_name = rec.get("shipName", "")
            flag = rec.get("flag", "")
            if isinstance(flag, dict):
                flag = flag.get("name", flag.get("code", ""))

            ship_type_raw = rec.get("shipType", "")
            if isinstance(ship_type_raw, dict):
                ship_type = ship_type_raw.get("description", "")
            else:
                ship_type = str(ship_type_raw)

            port_raw = rec.get("detentionPort", "")
            port_name = ""
            port_country = ""
            if isinstance(port_raw, dict):
                port_name = port_raw.get("name", "")
                country_raw = port_raw.get("country", {})
                port_country = country_raw.get("name", "") if isinstance(country_raw, dict) else str(country_raw)
            else:
                port_name = str(port_raw)

            authority = rec.get("detentionReportingAuthority", "")
            if isinstance(authority, dict):
                authority = authority.get("name", authority.get("code", ""))

            detention_date = rec.get("detentionDate", "")

            # Use center of Paris MOU region (European/North Atlantic)
            lon, lat = (w + e) / 2, (s + n) / 2

            observations.append({
                "obs_type": "governance",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"parismou-{imo}-{detention_date}",
                "source_name": "Paris MOU PSC",
                "quality_score": 0.95,
                "payload": {
                    "vessel_name": ship_name,
                    "imo": imo,
                    "flag_state": flag,
                    "ship_type": ship_type,
                    "detention_port": port_name,
                    "detention_country": port_country,
                    "detention_date": detention_date,
                    "reporting_authority": authority,
                },
            })

        logger.info("Paris MOU returned %d detention records", len(observations))
        return observations
