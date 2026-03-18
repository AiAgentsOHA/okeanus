"""IATI (International Aid Transparency Initiative) ocean grants adapter.

1,500+ reporting organizations, ocean-tagged development grants and
aid flows. The definitive source for who funds what in ocean development.

Uses the open Code for IATI Datastore Classic API (no auth required).
API docs: https://datastore.codeforiati.org/docs/api/
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Code for IATI Datastore Classic -- free, no API key required
BASE_URL = "https://datastore.codeforiati.org/api/1/access/activity.json"

# IATI sector codes related to ocean/marine
OCEAN_SECTOR_CODES = [
    "31310",  # Fishing policy and administrative management
    "31320",  # Fishery development
    "31381",  # Fishery education/training
    "31382",  # Fishery research
    "31391",  # Fishery services
]


class IatiOceanAdapter(BaseAdapter):
    """Connector for IATI Datastore Classic -- ocean development grants (no auth).

    Returns grant/loan flows for ocean/marine activities including
    fisheries, biodiversity, coastal, maritime sectors.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "iati_ocean"

    @property
    def source_url(self) -> str:
        return "https://iatistandard.org/"

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
        """Fetch IATI ocean-related aid activities.

        Extra params:
            sector_code: IATI sector code (default: '31310' = fisheries)
            country: ISO2 recipient country code
            limit: max records (default: 200)
        """
        sector_code = params.get("sector_code", "31310")
        country = params.get("country")
        limit = params.get("limit", 200)

        query_params: dict[str, Any] = {
            "sector": sector_code,
            "limit": min(limit, 500),
        }

        if country:
            query_params["recipient-country"] = country.upper()

        try:
            resp = await self._request("GET", BASE_URL, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("IATI fetch failed: %s", exc)
            return []

        activities = data.get("iati-activities", [])
        if not isinstance(activities, list):
            activities = []

        observations: list[dict[str, Any]] = []

        for entry in activities:
            act = entry.get("iati-activity", {})
            if not isinstance(act, dict):
                continue

            iati_id = act.get("iati-identifier", "")

            # Extract title
            title_obj = act.get("title", {})
            title = ""
            if isinstance(title_obj, dict):
                narrative = title_obj.get("narrative", "")
                if isinstance(narrative, dict):
                    title = narrative.get("text", str(narrative))
                elif isinstance(narrative, str):
                    title = narrative
                elif isinstance(narrative, list) and narrative:
                    title = narrative[0].get("text", str(narrative[0])) if isinstance(narrative[0], dict) else str(narrative[0])
                if not title:
                    title = title_obj.get("text", "").strip()

            # Extract dates
            start_date = ""
            dates = act.get("activity-date", [])
            if isinstance(dates, dict):
                dates = [dates]
            if isinstance(dates, list):
                for d in dates:
                    if isinstance(d, dict) and d.get("type") in ("1", "2"):
                        start_date = d.get("iso-date", "")
                        if start_date:
                            break

            try:
                ts = datetime.fromisoformat(start_date) if start_date else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            # Extract reporting org
            reporting = act.get("reporting-org", {})
            org_name = ""
            if isinstance(reporting, dict):
                narr = reporting.get("narrative", "")
                if isinstance(narr, dict):
                    org_name = narr.get("text", str(narr))
                elif isinstance(narr, str):
                    org_name = narr

            # Extract country
            recipient = act.get("recipient-country", {})
            country_code = ""
            if isinstance(recipient, dict):
                country_code = recipient.get("code", "")
            elif isinstance(recipient, list) and recipient:
                country_code = recipient[0].get("code", "") if isinstance(recipient[0], dict) else ""

            # Extract total transaction value
            total_value = 0.0
            transactions = act.get("transaction", [])
            if isinstance(transactions, dict):
                transactions = [transactions]
            if isinstance(transactions, list):
                for tx in transactions:
                    if isinstance(tx, dict):
                        val_obj = tx.get("value", {})
                        if isinstance(val_obj, dict):
                            try:
                                total_value += float(val_obj.get("text", 0))
                            except (ValueError, TypeError):
                                pass

            currency = act.get("default-currency", "USD")

            observations.append({
                "obs_type": "economic",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "source_id": f"iati-{iati_id}",
                "source_name": "IATI",
                "quality_score": 0.90,
                "payload": {
                    "iati_identifier": iati_id,
                    "title": title,
                    "reporting_org": org_name,
                    "recipient_country": country_code,
                    "sector_code": sector_code,
                    "total_value": total_value if total_value else None,
                    "currency": currency,
                    "start_date": start_date,
                },
            })

        logger.info("IATI returned %d ocean activities", len(observations))
        return observations
