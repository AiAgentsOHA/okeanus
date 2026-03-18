"""Ocean Info Hub (OIH) adapter — IOC-UNESCO ocean knowledge graph.

The Ocean InfoHub (OIH) project aggregates metadata about ocean datasets,
experts, training resources, and institutions from distributed ocean data
providers via a unified SPARQL/REST interface. No auth required.

When the SPARQL endpoint is unavailable (it uses a self-signed certificate
and has intermittent 502/503 errors), falls back to scraping the ODIS
catalogue at catalogue.odis.org and extracting JSON-LD metadata.

Data source: https://oceaninfohub.org/
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any

import httpx

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

SPARQL_URL = "https://graph.oceaninfohub.org/blazegraph/namespace/oih/sparql"
CATALOGUE_URL = "https://catalogue.odis.org"


class OceanInfoHubAdapter(BaseAdapter):
    """Connector for IOC-UNESCO Ocean Info Hub (no auth required).

    Queries the OIH knowledge graph for spatially-relevant ocean datasets,
    experts, and institutions.  Falls back to catalogue.odis.org HTML
    scraping when the SPARQL endpoint is unavailable.
    """

    def __init__(self, **kwargs: Any) -> None:
        # Only 1 retry for SPARQL — fail fast to catalogue fallback
        super().__init__(requests_per_second=1.0, timeout=15.0, max_retries=1, **kwargs)

    @property
    def source_name(self) -> str:
        return "ocean_info_hub"

    @property
    def source_url(self) -> str:
        return "https://oceaninfohub.org/"

    @property
    def update_frequency(self) -> str:
        return "weekly"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Search Ocean Info Hub for datasets related to an area.

        Extra params:
            search_type: 'dataset', 'expert', 'institution', 'training' (default 'dataset')
            keyword: text search keyword
            limit: max results (default 100)
        """
        w, s, e, n = bbox
        limit = params.get("limit", 100)
        search_type = params.get("search_type", "dataset")
        keyword = params.get("keyword", "ocean")

        # Try SPARQL endpoint first
        observations = await self._fetch_sparql(w, s, e, n, keyword, search_type, limit)

        # Fallback to catalogue scraping if SPARQL returned nothing
        if not observations:
            logger.info("SPARQL returned 0 results — falling back to ODIS catalogue")
            observations = await self._fetch_catalogue(w, s, e, n, keyword, limit, time_start)

        logger.info("Ocean Info Hub returned %d %s records", len(observations), search_type)
        return observations

    async def _fetch_sparql(
        self,
        w: float, s: float, e: float, n: float,
        keyword: str,
        search_type: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Try the SPARQL endpoint (may fail due to SSL or downtime)."""
        type_map = {
            "dataset": "schema:Dataset",
            "expert": "schema:Person",
            "institution": "schema:Organization",
            "training": "schema:Course",
        }
        rdf_type = type_map.get(search_type, "schema:Dataset")

        sparql = f"""
PREFIX schema: <https://schema.org/>
PREFIX geo: <http://www.opengis.net/ont/geosparql#>

SELECT ?item ?name ?description ?url ?lat ?lon
WHERE {{
  ?item a {rdf_type} .
  ?item schema:name ?name .
  OPTIONAL {{ ?item schema:description ?description }}
  OPTIONAL {{ ?item schema:url ?url }}
  OPTIONAL {{
    ?item schema:spatialCoverage ?place .
    ?place schema:geo ?geo .
    ?geo schema:latitude ?lat .
    ?geo schema:longitude ?lon .
  }}
  FILTER(CONTAINS(LCASE(?name), LCASE("{keyword}")))
}}
LIMIT {limit}
"""
        try:
            # Use verify=False — the endpoint has a self-signed certificate
            client = httpx.AsyncClient(timeout=self._timeout, verify=False, follow_redirects=True)
            try:
                resp = await self._request(
                    "POST",
                    SPARQL_URL,
                    client=client,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/sparql-results+json",
                    },
                    params={"query": sparql},
                )
                data = resp.json()
            finally:
                await client.aclose()
        except Exception as exc:
            logger.warning("Ocean Info Hub SPARQL failed: %s", exc)
            return []

        bindings = data.get("results", {}).get("bindings", [])
        observations: list[dict[str, Any]] = []

        for rec in bindings:
            lon_val = rec.get("lon", {}).get("value")
            lat_val = rec.get("lat", {}).get("value")

            if lon_val and lat_val:
                try:
                    lon, lat = float(lon_val), float(lat_val)
                except (ValueError, TypeError):
                    lon, lat = (w + e) / 2, (s + n) / 2
            else:
                lon, lat = (w + e) / 2, (s + n) / 2

            name = rec.get("name", {}).get("value", "")
            item_url = rec.get("item", {}).get("value", "")

            observations.append({
                "obs_type": "physical",
                "timestamp": datetime.now(),
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"oih-{item_url.split('/')[-1] if item_url else name[:20]}",
                "source_name": "Ocean Info Hub",
                "quality_score": 0.7,
                "payload": {
                    "name": name,
                    "description": rec.get("description", {}).get("value", ""),
                    "url": rec.get("url", {}).get("value", item_url),
                    "type": search_type,
                    "graph_uri": item_url,
                },
            })

        return observations

    async def _fetch_catalogue(
        self,
        w: float, s: float, e: float, n: float,
        keyword: str,
        limit: int,
        time_start: datetime,
    ) -> list[dict[str, Any]]:
        """Scrape catalogue.odis.org search results + JSON-LD from view pages."""
        # Step 1: search the catalogue for view IDs
        search_url = f"{CATALOGUE_URL}/search"
        try:
            client = httpx.AsyncClient(timeout=self._timeout, verify=False, follow_redirects=True)
            try:
                resp = await self._request(
                    "GET", search_url, client=client,
                    params={"q": keyword},
                )
                html = resp.text
            finally:
                await client.aclose()
        except Exception as exc:
            logger.error("ODIS catalogue search failed: %s", exc)
            return []

        view_ids = list(dict.fromkeys(re.findall(r"/view/(\d+)", html)))
        if not view_ids:
            logger.warning("ODIS catalogue returned no results for %r", keyword)
            return []

        # Step 2: fetch JSON-LD from each view page (up to limit)
        observations: list[dict[str, Any]] = []
        cx, cy = (w + e) / 2.0, (s + n) / 2.0

        for vid in view_ids[:limit]:
            view_url = f"{CATALOGUE_URL}/view/{vid}"
            try:
                client = httpx.AsyncClient(timeout=self._timeout, verify=False, follow_redirects=True)
                try:
                    resp = await self._request("GET", view_url, client=client)
                    page_html = resp.text
                finally:
                    await client.aclose()
            except Exception:
                continue

            # Extract JSON-LD
            ld_matches = re.findall(
                r"<script\s+type=[\"']application/ld\+json[\"']>(.*?)</script>",
                page_html, re.DOTALL,
            )
            if not ld_matches:
                continue

            try:
                ld = json.loads(ld_matches[0])
            except (json.JSONDecodeError, IndexError):
                continue

            name = ld.get("name", "")
            if not name:
                continue

            observations.append({
                "obs_type": "physical",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [cx, cy]},
                "source_id": f"oih-catalogue-{vid}",
                "source_name": "Ocean Info Hub",
                "quality_score": 0.6,
                "payload": {
                    "name": name,
                    "description": str(ld.get("description", ""))[:500],
                    "url": ld.get("url", view_url),
                    "type": ld.get("@type", ""),
                    "keywords": ld.get("keywords", []),
                    "graph_uri": view_url,
                },
            })

        return observations
