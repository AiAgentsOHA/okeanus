"""US Federal Register adapter — maritime regulations and fisheries rules.

The Federal Register API provides programmatic access to US federal
regulations including NOAA fisheries closures, marine sanctuary rules,
and maritime safety notices. No auth required.

Data source: https://www.federalregister.gov/developers
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"


class FedRegisterAdapter(BaseAdapter):
    """Connector for US Federal Register API (no auth required)."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=5.0, **kwargs)

    @property
    def source_name(self) -> str:
        return "fed_register"

    @property
    def source_url(self) -> str:
        return "https://www.federalregister.gov/"

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
        """Fetch marine/fisheries regulations from the Federal Register.

        Extra params:
            search_term: custom search (default 'marine fisheries')
            doc_type: 'RULE', 'PRORULE', 'NOTICE' (default all)
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)
        search_term = params.get("search_term", "marine fisheries ocean")
        doc_type = params.get("doc_type")

        api_params: dict[str, Any] = {
            "conditions[term]": search_term,
            "conditions[agencies][]": "national-oceanic-and-atmospheric-administration",
            "conditions[publication_date][gte]": time_start.strftime("%m/%d/%Y"),
            "conditions[publication_date][lte]": time_end.strftime("%m/%d/%Y"),
            "per_page": min(limit, 1000),
            "order": "newest",
        }

        if doc_type:
            api_params["conditions[type][]"] = doc_type

        try:
            resp = await self._request("GET", BASE_URL, params=api_params)
            data = resp.json()
        except Exception as exc:
            logger.error("Federal Register fetch failed: %s", exc)
            return []

        results = data.get("results", [])
        w, s, e, n = bbox
        lon_center = (w + e) / 2
        lat_center = (s + n) / 2

        observations: list[dict[str, Any]] = []

        for rec in results[:limit]:
            if not isinstance(rec, dict):
                continue

            pub_date = rec.get("publication_date", "")
            try:
                ts = datetime.fromisoformat(pub_date) if pub_date else time_start
            except ValueError:
                ts = time_start

            observations.append({
                "obs_type": "physical",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [lon_center, lat_center]},
                "source_id": f"fedreg-{rec.get('document_number', '')}",
                "source_name": "US Federal Register",
                "quality_score": 0.95,
                "payload": {
                    "title": rec.get("title", ""),
                    "document_number": rec.get("document_number", ""),
                    "type": rec.get("type", ""),
                    "agencies": [a.get("name", "") for a in rec.get("agencies", [])],
                    "abstract": rec.get("abstract", ""),
                    "publication_date": pub_date,
                    "effective_date": rec.get("effective_on", ""),
                    "html_url": rec.get("html_url", ""),
                    "pdf_url": rec.get("pdf_url", ""),
                    "cfr_references": rec.get("cfr_references", []),
                },
            })

        logger.info("Federal Register returned %d documents", len(observations))
        return observations
