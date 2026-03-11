"""IATI (International Aid Transparency Initiative) ocean grants adapter.

1,500+ reporting organizations, ocean-tagged development grants and
aid flows. The definitive source for who funds what in ocean development.

API: REST at developer.iatistandard.org.
No auth required.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.iatistandard.org/datastore"

# IATI sector codes related to ocean/marine
OCEAN_SECTORS = {
    "31310": "Fishing policy and administrative management",
    "31320": "Fishery development",
    "31381": "Fishery education/training",
    "31382": "Fishery research",
    "31391": "Fishery services",
    "41010": "Environmental policy and admin",
    "41030": "Biodiversity",
    "41081": "Flood prevention/control",
    "41082": "Environmental education/training",
    "14040": "Water resources protection",
    "23210": "Energy policy — includes offshore",
    "21020": "Transport policy — includes maritime",
}


class IatiOceanAdapter(BaseAdapter):
    """Connector for IATI Datastore — ocean development grants (no auth).

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
            query: text search term (e.g. 'marine', 'ocean', 'coastal')
            limit: max records (default: 200)
        """
        sector_code = params.get("sector_code", "31310")
        country = params.get("country")
        query = params.get("query", "ocean OR marine OR coastal OR fisheries")
        limit = params.get("limit", 200)

        url = f"{BASE_URL}/activity/select"
        q_parts = [f"sector_code:{sector_code}"]
        if country:
            q_parts.append(f"recipient_country_code:{country.upper()}")

        fq = f"activity_date_start_actual_f:[{time_start.strftime('%Y-%m-%dT00:00:00Z')} TO {time_end.strftime('%Y-%m-%dT23:59:59Z')}]"

        query_params: dict[str, Any] = {
            "q": query,
            "fq": fq,
            "fl": "iati_identifier,title_narrative,description_narrative,activity_date_start_actual_f,activity_date_end_actual_f,reporting_org_narrative,recipient_country_code,sector_code,transaction_value,default_currency,activity_status_code",
            "rows": limit,
            "wt": "json",
        }

        try:
            resp = await self._request("GET", url, params=query_params)
            data = resp.json()
        except Exception as exc:
            logger.error("IATI fetch failed: %s", exc)
            return []

        docs = data.get("response", {}).get("docs", [])
        if not isinstance(docs, list):
            docs = []

        observations: list[dict[str, Any]] = []

        for doc in docs:
            if not isinstance(doc, dict):
                continue

            iati_id = doc.get("iati_identifier", "")
            title = doc.get("title_narrative", [""])[0] if isinstance(doc.get("title_narrative"), list) else str(doc.get("title_narrative", ""))
            start_date = doc.get("activity_date_start_actual_f", "")

            try:
                ts = datetime.fromisoformat(start_date.replace("Z", "+00:00")) if start_date else datetime.now()
            except (ValueError, TypeError):
                ts = datetime.now()

            values = doc.get("transaction_value", [])
            total_value = sum(float(v) for v in values if v) if isinstance(values, list) else None

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
                    "reporting_org": doc.get("reporting_org_narrative", [""])[0] if isinstance(doc.get("reporting_org_narrative"), list) else "",
                    "recipient_country": doc.get("recipient_country_code", []),
                    "sector_codes": doc.get("sector_code", []),
                    "total_value": total_value,
                    "currency": doc.get("default_currency", "USD"),
                    "status": doc.get("activity_status_code", ""),
                    "start_date": start_date,
                    "end_date": doc.get("activity_date_end_actual_f", ""),
                },
            })

        logger.info("IATI returned %d ocean activities", len(observations))
        return observations
