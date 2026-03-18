"""NCBI Marine Genomics adapter — marine organism genome/sequence data.

NCBI (National Center for Biotechnology Information) hosts genome
assemblies, sequences, and publications for marine organisms.
The Entrez E-utilities API provides programmatic access.

API: REST at eutils.ncbi.nlm.nih.gov. No auth required (but API key
recommended for higher rate limits).

Data source: https://www.ncbi.nlm.nih.gov/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class NcbiMarineAdapter(BaseAdapter):
    """Connector for NCBI marine genomics data (no auth required).

    Returns genome assemblies and nucleotide records for marine
    organisms via NCBI's Entrez E-utilities.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(requests_per_second=3.0, timeout=60.0, **kwargs)
        self._api_key = os.environ.get("NCBI_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "ncbi_marine"

    @property
    def source_url(self) -> str:
        return "https://www.ncbi.nlm.nih.gov/"

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
        """Fetch NCBI marine organism genome/sequence records.

        Extra params:
            organism: organism name (default 'marine')
            database: 'assembly' (default), 'nucleotide', 'biosample'
            query: custom search term
            limit: max records (default 100)
        """
        limit = params.get("limit", 100)
        organism = params.get("organism", "marine")
        database = params.get("database", "assembly")
        query = params.get("query")

        if not query:
            # Build marine-focused search (no PDAT range in term — breaks assembly db)
            if organism != "marine":
                query = f'"{organism}"[Organism]'
            else:
                query = "(marine[All Fields] OR ocean[All Fields])"

        # Step 1: esearch to get IDs
        search_params: dict[str, Any] = {
            "db": database,
            "term": query,
            "retmax": limit,
            "retmode": "json",
            "datetype": "GRLS",
            "mindate": time_start.strftime("%Y/%m/%d"),
            "maxdate": time_end.strftime("%Y/%m/%d"),
        }
        if self._api_key:
            search_params["api_key"] = self._api_key

        try:
            resp = await self._request("GET", f"{EUTILS_BASE}/esearch.fcgi", params=search_params)
            search_data = resp.json()
        except Exception as exc:
            logger.error("NCBI esearch failed: %s", exc)
            return []

        result = search_data.get("esearchresult", {})
        id_list = result.get("idlist", [])

        if not id_list:
            return []

        # Step 2: esummary to get details
        summary_params: dict[str, Any] = {
            "db": database,
            "id": ",".join(id_list[:limit]),
            "retmode": "json",
        }
        if self._api_key:
            summary_params["api_key"] = self._api_key

        try:
            resp = await self._request("GET", f"{EUTILS_BASE}/esummary.fcgi", params=summary_params)
            summary_data = resp.json()
        except Exception as exc:
            logger.error("NCBI esummary failed: %s", exc)
            return []

        records = summary_data.get("result", {})
        uid_list = records.get("uids", id_list)

        w, s, e, n = bbox
        center_lon = (w + e) / 2
        center_lat = (s + n) / 2

        observations: list[dict[str, Any]] = []

        for uid in uid_list:
            if len(observations) >= limit:
                break

            rec = records.get(str(uid), {})
            if not isinstance(rec, dict):
                continue

            organism_name = rec.get("organism") or rec.get("speciesname", "")
            title = rec.get("title") or rec.get("assemblyname", "")

            # Parse date
            date_str = rec.get("sortdate") or rec.get("createdate", "")
            try:
                ts = datetime.fromisoformat(date_str[:10]) if date_str else time_start
            except (ValueError, TypeError):
                ts = time_start

            observations.append({
                "obs_type": "biological",
                "timestamp": ts,
                "geometry": {"type": "Point", "coordinates": [center_lon, center_lat]},
                "source_id": f"ncbi-{database}-{uid}",
                "source_name": "NCBI",
                "quality_score": 0.95,
                "payload": {
                    "uid": str(uid),
                    "database": database,
                    "title": str(title)[:200],
                    "organism": organism_name,
                    "taxonomy_id": rec.get("taxid") or rec.get("speciestaxid", ""),
                    "accession": rec.get("assemblyaccession") or rec.get("accessionversion", ""),
                    "status": rec.get("assemblystatus") or rec.get("status", ""),
                    "genome_size_mb": rec.get("total_length"),
                    "scaffold_count": rec.get("scaffoldcount"),
                },
            })

        logger.info("NCBI returned %d %s records", len(observations), database)
        return observations
