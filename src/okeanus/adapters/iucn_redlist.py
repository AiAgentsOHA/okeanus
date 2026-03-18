"""IUCN Red List adapter — marine species conservation status.

Provides access to the IUCN Red List API v4 for marine species assessments
including threat categories, population trends, and habitat information.
Requires a free API token from https://api.iucnredlist.org/users/sign_up

Data source: https://www.iucnredlist.org/
API docs:    https://api.iucnredlist.org/api-docs/index.html
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.iucnredlist.org/api/v4"

# IUCN v4 system code for marine species
MARINE_SYSTEM_CODE = "2"


class IucnRedlistAdapter(BaseAdapter):
    """Connector for IUCN Red List API v4 (Bearer token required).

    The v3 API was retired in March 2025. This adapter uses the v4 API
    with Bearer token authentication.
    """

    def __init__(self, api_token: str = "", **kwargs: Any) -> None:
        super().__init__(requests_per_second=2.0, **kwargs)
        self._api_token = api_token or os.environ.get("IUCN_API_KEY", "")

    @property
    def source_name(self) -> str:
        return "iucn_redlist"

    @property
    def source_url(self) -> str:
        return BASE_URL

    @property
    def update_frequency(self) -> str:
        return "yearly"

    def _auth_headers(self) -> dict[str, str]:
        if self._api_token:
            return {"Authorization": f"Bearer {self._api_token}"}
        return {}

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch marine species from the IUCN Red List v4 API.

        Extra params:
            species_name: search by species name (genus_name.species_name format)
            category: filter by threat category code (e.g. 'CR', 'EN', 'VU')
            limit: max records (default 100)
        """
        if not self._api_token:
            logger.warning("IUCN Red List adapter requires api_token (free at api.iucnredlist.org)")
            return []

        limit = params.get("limit", 100)
        species_name = params.get("species_name")
        category = params.get("category")
        headers = self._auth_headers()

        if species_name:
            return await self._fetch_by_species(
                species_name, bbox, time_start, headers, category, limit,
            )

        if category:
            return await self._fetch_by_category(
                category, bbox, time_start, headers, limit,
            )

        # Default: fetch marine species assessments via systems endpoint
        return await self._fetch_marine_assessments(
            bbox, time_start, headers, category, limit,
        )

    async def _fetch_by_species(
        self,
        species_name: str,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        headers: dict[str, str],
        category: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Search by scientific name using v4 taxa endpoint."""
        parts = species_name.strip().split(maxsplit=1)
        if len(parts) == 2:
            genus, species = parts
            url = f"{BASE_URL}/taxa/scientific_name"
            query: dict[str, str] = {
                "genus_name": genus,
                "species_name": species,
            }
        else:
            # Try as a family or genus lookup
            url = f"{BASE_URL}/taxa/scientific_name"
            query = {"genus_name": species_name, "species_name": ""}

        try:
            resp = await self._request("GET", url, params=query, headers=headers)
            data = resp.json()
        except Exception as exc:
            logger.error("IUCN Red List taxa search failed: %s", exc)
            return []

        taxon = data.get("taxon", {})
        if not taxon:
            return []

        # Get assessment details for this taxon
        sis_id = taxon.get("sis_id")
        if not sis_id:
            return []

        return self._taxon_to_observations(
            taxon, bbox, time_start, category, limit,
        )

    async def _fetch_by_category(
        self,
        category: str,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        headers: dict[str, str],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch assessments by Red List category code."""
        url = f"{BASE_URL}/red_list_categories/{category}"
        query: dict[str, Any] = {"latest": "true", "page": 1}

        try:
            resp = await self._request("GET", url, params=query, headers=headers)
            data = resp.json()
        except Exception as exc:
            logger.error("IUCN Red List category fetch failed: %s", exc)
            return []

        assessments = data.get("assessments", [])
        return self._assessments_to_observations(
            assessments[:limit], bbox, time_start, category,
        )

    async def _fetch_marine_assessments(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        headers: dict[str, str],
        category: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch marine system assessments (system code 2)."""
        url = f"{BASE_URL}/systems/{MARINE_SYSTEM_CODE}"
        query: dict[str, Any] = {"latest": "true", "page": 1}

        try:
            resp = await self._request("GET", url, params=query, headers=headers)
            data = resp.json()
        except Exception as exc:
            logger.error("IUCN Red List marine fetch failed: %s", exc)
            return []

        assessments = data.get("assessments", [])
        return self._assessments_to_observations(
            assessments[:limit], bbox, time_start, category,
        )

    def _taxon_to_observations(
        self,
        taxon: dict[str, Any],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        category: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Convert a v4 taxon record into observation dicts."""
        w, s, e, n = bbox
        lon = (w + e) / 2
        lat = (s + n) / 2

        observations: list[dict[str, Any]] = []
        sis_id = taxon.get("sis_id", "")
        scientific_name = taxon.get("scientific_name", "")

        common_names = taxon.get("common_names", [])
        main_common = ""
        for cn in common_names:
            if cn.get("main"):
                main_common = cn.get("name", "")
                break
        if not main_common and common_names:
            main_common = common_names[0].get("name", "")

        observations.append({
            "obs_type": "biological",
            "timestamp": time_start,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "source_id": f"iucn-{sis_id}",
            "source_name": "IUCN Red List",
            "quality_score": 0.95,
            "payload": {
                "scientific_name": scientific_name,
                "common_name": main_common,
                "class": taxon.get("class_name", ""),
                "order": taxon.get("order_name", ""),
                "family": taxon.get("family_name", ""),
                "kingdom": taxon.get("kingdom_name", ""),
                "sis_id": sis_id,
            },
        })

        logger.info("IUCN Red List returned %d species", len(observations))
        return observations[:limit]

    def _assessments_to_observations(
        self,
        assessments: list[dict[str, Any]],
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        category: str | None,
    ) -> list[dict[str, Any]]:
        """Convert v4 assessment list into observation dicts."""
        w, s, e, n = bbox
        lon = (w + e) / 2
        lat = (s + n) / 2

        observations: list[dict[str, Any]] = []

        for rec in assessments:
            if not isinstance(rec, dict):
                continue

            rec_category = rec.get("red_list_category_code", "")
            if category and rec_category != category:
                continue

            sis_id = rec.get("sis_taxon_id", rec.get("assessment_id", ""))
            scientific_name = rec.get("taxon_scientific_name", "")
            year_published = rec.get("year_published", "")

            observations.append({
                "obs_type": "biological",
                "timestamp": time_start,
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "source_id": f"iucn-{sis_id}",
                "source_name": "IUCN Red List",
                "quality_score": 0.95,
                "payload": {
                    "scientific_name": scientific_name,
                    "common_name": "",
                    "category": rec_category,
                    "assessment_id": rec.get("assessment_id"),
                    "year_published": year_published,
                    "url": rec.get("url", ""),
                    "criteria": rec.get("criteria", ""),
                    "possibly_extinct": rec.get("possibly_extinct", False),
                    "latest": rec.get("latest", True),
                },
            })

        logger.info("IUCN Red List returned %d species", len(observations))
        return observations
