"""Cross-source entity resolution — dedup, fuzzy match, and merge.

Finds duplicate entities across different data sources and merges them
into canonical records. Uses:
- Exact match on identifiers (IMO, MMSI, ISO codes)
- Fuzzy name matching via SequenceMatcher (stdlib, no new deps)
- Spatial proximity for geo-located entities
- Ontology-aware type compatibility and cross-ref ID matching
- Country normalization for consistent comparison
"""

from __future__ import annotations

import logging
import re
import uuid
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.transform.ontology import (
    normalize_country,
    types_compatible,
    extract_canonical_name,
    extract_cross_ref_ids,
    SPECIES_SOURCES,
    COUNTRY_SOURCES,
    INFRASTRUCTURE_SOURCES,
    REGION_SOURCES,
)

logger = logging.getLogger(__name__)

# Characters to strip for normalized comparison
_STRIP_RE = re.compile(r"[^a-z0-9\s]")

# Source groups that can produce equivalent entities
_EQUIVALENCE_GROUPS: list[frozenset[str]] = [
    SPECIES_SOURCES,
    COUNTRY_SOURCES,
    INFRASTRUCTURE_SOURCES,
    REGION_SOURCES,
]


def _sources_in_same_group(src_a: str, src_b: str) -> bool:
    """Check if two sources belong to the same equivalence group."""
    for group in _EQUIVALENCE_GROUPS:
        if src_a in group and src_b in group:
            return True
    return False


def _normalize_name(name: str) -> str:
    """Normalize entity name for comparison: lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = _STRIP_RE.sub("", name)
    return " ".join(name.split())


def _fuzzy_score(a: str, b: str) -> float:
    """Fuzzy similarity between two strings. Returns 0.0-1.0."""
    na, nb = _normalize_name(a), _normalize_name(b)
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


class EntityResolver:
    """Cross-source entity resolution engine."""

    def __init__(
        self,
        name_threshold: float = 0.85,
        spatial_km: float = 5.0,
        embedding_threshold: float = 0.85,
    ) -> None:
        self._name_threshold = name_threshold
        self._spatial_km = spatial_km
        self._embedding_threshold = embedding_threshold

    async def find_duplicates(
        self,
        session: AsyncSession,
        entity_type: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Find candidate duplicate entity pairs across different sources.

        Strategy (in priority order):
        1. Exact identifier match (different source_name, same identifier)
        2. Cross-reference ID match (e.g. AphiaID shared between OBIS/WoRMS)
        3. Exact normalized name match (different source_name)
        4. Fuzzy name match above threshold
        5. Country normalization match (different representations of same country)

        Uses ontology type hierarchy to allow matching across compatible types
        (e.g. species_observation can match taxon).
        """
        candidates: list[dict[str, Any]] = []

        # Strategy 1: Exact identifier match across sources
        id_matches = await self._exact_identifier_matches(session, entity_type, limit)
        candidates.extend(id_matches)

        # Strategy 2: Cross-reference ID matching via ontology
        xref_matches = await self._cross_ref_matches(session, entity_type, limit)
        candidates.extend(xref_matches)

        # Strategy 3+4: Name-based matching (ontology-aware)
        name_matches = await self._name_matches(session, entity_type, limit)
        candidates.extend(name_matches)

        # Strategy 5: Country normalization
        country_matches = await self._country_norm_matches(session, limit)
        candidates.extend(country_matches)

        # Deduplicate candidate pairs (A,B same as B,A)
        seen: set[tuple[str, str]] = set()
        unique: list[dict[str, Any]] = []
        for c in candidates:
            pair = tuple(sorted([c["entity_a_id"], c["entity_b_id"]]))
            if pair not in seen:
                seen.add(pair)
                unique.append(c)

        return sorted(unique, key=lambda x: x["confidence"], reverse=True)[:limit]

    async def _exact_identifier_matches(
        self,
        session: AsyncSession,
        entity_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Find entities with the same identifier from different sources."""
        type_filter = "AND a.entity_type = :etype" if entity_type else ""
        params: dict[str, Any] = {"lim": limit}
        if entity_type:
            params["etype"] = entity_type

        sql = text(f"""
            SELECT a.id AS a_id, a.name AS a_name, a.source_name AS a_src,
                   a.identifier AS a_ident, a.entity_type AS a_type,
                   b.id AS b_id, b.name AS b_name, b.source_name AS b_src,
                   b.identifier AS b_ident
            FROM entities a
            JOIN entities b ON a.identifier = b.identifier
                AND a.entity_type = b.entity_type
                AND a.source_name < b.source_name
                AND a.id != b.id
            WHERE a.identifier IS NOT NULL
                AND a.identifier != ''
                {type_filter}
            LIMIT :lim
        """)
        rows = (await session.execute(sql, params)).fetchall()

        return [
            {
                "entity_a_id": str(row.a_id),
                "entity_a_name": row.a_name,
                "entity_a_source": row.a_src,
                "entity_b_id": str(row.b_id),
                "entity_b_name": row.b_name,
                "entity_b_source": row.b_src,
                "match_type": "exact_identifier",
                "identifier": row.a_ident,
                "entity_type": row.a_type,
                "confidence": 0.95,
            }
            for row in rows
        ]

    async def _cross_ref_matches(
        self,
        session: AsyncSession,
        entity_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Find entities that share cross-reference IDs in their payloads.

        Uses ontology CROSS_REF_IDS mapping to extract IDs like AphiaID
        that appear in multiple sources (e.g. OBIS and WoRMS).
        """
        type_filter = "AND entity_type = :etype" if entity_type else ""
        params: dict[str, Any] = {"lim": 500}
        if entity_type:
            params["etype"] = entity_type

        sql = text(f"""
            SELECT id, name, source_name, entity_type, identifier, payload
            FROM entities
            WHERE payload IS NOT NULL
                {type_filter}
            ORDER BY entity_type, source_name
            LIMIT :lim
        """)
        rows = (await session.execute(sql, params)).fetchall()

        # Build index: (id_system, id_value) -> list of entities
        xref_index: dict[tuple[str, str], list[Any]] = {}
        for row in rows:
            payload = row.payload or {}
            xrefs = extract_cross_ref_ids(row.source_name, payload)
            for id_system, id_val in xrefs.items():
                xref_index.setdefault((id_system, id_val), []).append(row)

        results: list[dict[str, Any]] = []
        for key, group in xref_index.items():
            if len(group) < 2:
                continue
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    if a.source_name == b.source_name:
                        continue
                    if not types_compatible(a.entity_type, b.entity_type):
                        continue
                    # Cross-ref ID match is high confidence
                    confidence = 0.92
                    # Boost if names also match
                    if a.name and b.name:
                        name_score = _fuzzy_score(a.name, b.name)
                        if name_score > 0.8:
                            confidence = min(0.99, confidence + 0.05)
                    results.append({
                        "entity_a_id": str(a.id),
                        "entity_a_name": a.name,
                        "entity_a_source": a.source_name,
                        "entity_b_id": str(b.id),
                        "entity_b_name": b.name,
                        "entity_b_source": b.source_name,
                        "match_type": "cross_ref_id",
                        "cross_ref": f"{key[0]}={key[1]}",
                        "entity_type": a.entity_type,
                        "confidence": confidence,
                    })
                    if len(results) >= limit:
                        return results
        return results

    async def _country_norm_matches(
        self,
        session: AsyncSession,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Find country entities that represent the same country with different names.

        Uses ontology country normalization to detect e.g.
        'United States of America' (IATI) == 'US' (IUU Fishing Index).
        """
        sql = text("""
            SELECT id, name, source_name, entity_type, identifier, country
            FROM entities
            WHERE entity_type = 'country'
            ORDER BY name
            LIMIT :lim
        """)
        rows = (await session.execute(sql, {"lim": 500})).fetchall()

        # Group by normalized country code
        by_code: dict[str, list[Any]] = {}
        for row in rows:
            # Try identifier first (often ISO code), then name
            code = normalize_country(row.identifier) or normalize_country(row.name) or normalize_country(row.country)
            if code:
                by_code.setdefault(code, []).append(row)

        results: list[dict[str, Any]] = []
        for code, group in by_code.items():
            if len(group) < 2:
                continue
            for i, a in enumerate(group):
                for b in group[i + 1:]:
                    if a.source_name == b.source_name:
                        continue
                    if str(a.id) == str(b.id):
                        continue
                    # Same normalized country code = high confidence
                    confidence = 0.93
                    # Boost if sources are in the same equivalence group
                    if _sources_in_same_group(a.source_name, b.source_name):
                        confidence = 0.96
                    results.append({
                        "entity_a_id": str(a.id),
                        "entity_a_name": a.name,
                        "entity_a_source": a.source_name,
                        "entity_b_id": str(b.id),
                        "entity_b_name": b.name,
                        "entity_b_source": b.source_name,
                        "match_type": "country_normalization",
                        "normalized_code": code,
                        "entity_type": "country",
                        "confidence": confidence,
                    })
                    if len(results) >= limit:
                        return results
        return results

    async def _name_matches(
        self,
        session: AsyncSession,
        entity_type: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Find entities with similar names across sources.

        Fetches cross-source entity pairs, then applies fuzzy matching in Python.
        Uses ontology type hierarchy to allow matching across compatible types
        (e.g. species_observation can match taxon if sources are in the same group).
        Also extracts canonical names from payloads when available.
        """
        type_filter = "AND entity_type = :etype" if entity_type else ""
        params: dict[str, Any] = {"lim": 500}  # fetch more, filter in Python
        if entity_type:
            params["etype"] = entity_type

        sql = text(f"""
            SELECT id, name, source_name, entity_type, identifier, payload
            FROM entities
            WHERE name IS NOT NULL AND name != ''
                {type_filter}
            ORDER BY entity_type, name
            LIMIT :lim
        """)
        rows = (await session.execute(sql, params)).fetchall()

        # Group by entity_type for efficient comparison
        by_type: dict[str, list[Any]] = {}
        for row in rows:
            by_type.setdefault(row.entity_type, []).append(row)

        results: list[dict[str, Any]] = []

        # Compare within same type
        for etype, entities in by_type.items():
            for i, a in enumerate(entities):
                for b in entities[i + 1:]:
                    if a.source_name == b.source_name:
                        continue

                    score = self._ontology_name_score(a, b)
                    if score >= self._name_threshold:
                        match_type = "exact_name" if score >= 0.99 else "fuzzy_name"
                        results.append({
                            "entity_a_id": str(a.id),
                            "entity_a_name": a.name,
                            "entity_a_source": a.source_name,
                            "entity_b_id": str(b.id),
                            "entity_b_name": b.name,
                            "entity_b_source": b.source_name,
                            "match_type": match_type,
                            "entity_type": etype,
                            "confidence": round(score, 4),
                        })

                    if len(results) >= limit:
                        return results

        # Compare across compatible types (ontology-aware)
        type_list = list(by_type.keys())
        for i, type_a in enumerate(type_list):
            for type_b in type_list[i + 1:]:
                if not types_compatible(type_a, type_b):
                    continue
                for a in by_type[type_a]:
                    for b in by_type[type_b]:
                        if a.source_name == b.source_name:
                            continue
                        score = self._ontology_name_score(a, b)
                        # Slightly higher threshold for cross-type matches
                        if score >= min(0.92, self._name_threshold + 0.05):
                            results.append({
                                "entity_a_id": str(a.id),
                                "entity_a_name": a.name,
                                "entity_a_source": a.source_name,
                                "entity_b_id": str(b.id),
                                "entity_b_name": b.name,
                                "entity_b_source": b.source_name,
                                "match_type": "cross_type_name",
                                "entity_type": f"{type_a}+{type_b}",
                                "confidence": round(score, 4),
                            })
                        if len(results) >= limit:
                            return results

        return results

    def _ontology_name_score(self, a: Any, b: Any) -> float:
        """Compute name similarity using ontology-aware canonical name extraction.

        Tries canonical payload names first, falls back to entity name field.
        """
        # Try canonical names from payload
        a_payload = a.payload or {} if hasattr(a, 'payload') and a.payload else {}
        b_payload = b.payload or {} if hasattr(b, 'payload') and b.payload else {}

        a_canonical = extract_canonical_name(a.source_name, a_payload)
        b_canonical = extract_canonical_name(b.source_name, b_payload)

        # Score using canonical names if available
        name_a = a_canonical or a.name
        name_b = b_canonical or b.name

        score = _fuzzy_score(name_a, name_b)

        # If canonical names exist and differ from entity names, also try entity names
        if a_canonical and a_canonical != a.name:
            alt_score = _fuzzy_score(a.name, name_b)
            score = max(score, alt_score)
        if b_canonical and b_canonical != b.name:
            alt_score = _fuzzy_score(name_a, b.name)
            score = max(score, alt_score)

        # Boost if sources are in same equivalence group
        if _sources_in_same_group(a.source_name, b.source_name) and score > 0.7:
            score = min(1.0, score * 1.05)

        return score

    async def find_spatial_duplicates(
        self,
        session: AsyncSession,
        entity_type: str | None = None,
        distance_km: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find entities that are spatially close AND have similar names."""
        km = distance_km or self._spatial_km
        degrees = km / 111.0  # rough km-to-degree conversion

        type_filter = "AND a.entity_type = :etype" if entity_type else ""
        params: dict[str, Any] = {"dist": degrees, "lim": limit}
        if entity_type:
            params["etype"] = entity_type

        sql = text(f"""
            SELECT a.id AS a_id, a.name AS a_name, a.source_name AS a_src,
                   a.entity_type AS a_type,
                   b.id AS b_id, b.name AS b_name, b.source_name AS b_src,
                   ST_Distance(a.geometry, b.geometry) AS geom_dist
            FROM entities a
            JOIN entities b ON a.entity_type = b.entity_type
                AND a.source_name < b.source_name
                AND a.id != b.id
                AND a.geometry IS NOT NULL
                AND b.geometry IS NOT NULL
                AND ST_DWithin(a.geometry, b.geometry, :dist)
            WHERE 1=1
                {type_filter}
            ORDER BY geom_dist
            LIMIT :lim
        """)
        rows = (await session.execute(sql, params)).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            name_score = _fuzzy_score(row.a_name, row.b_name)
            # Spatial proximity + name similarity = high confidence
            spatial_score = max(0, 1.0 - (float(row.geom_dist) / degrees))
            combined = 0.5 * name_score + 0.5 * spatial_score

            if combined >= 0.6:
                results.append({
                    "entity_a_id": str(row.a_id),
                    "entity_a_name": row.a_name,
                    "entity_a_source": row.a_src,
                    "entity_b_id": str(row.b_id),
                    "entity_b_name": row.b_name,
                    "entity_b_source": row.b_src,
                    "match_type": "spatial_name",
                    "entity_type": row.a_type,
                    "name_score": round(name_score, 4),
                    "spatial_score": round(spatial_score, 4),
                    "confidence": round(combined, 4),
                })

        return results

    async def merge_entities(
        self,
        session: AsyncSession,
        keep_id: uuid.UUID,
        merge_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Merge two entities: keep one, redirect references from the other.

        Updates all foreign-key references (knowledge_edges, embeddings, flows)
        to point to the kept entity. Merges payload fields.
        Marks the merged entity with status='merged'.
        """
        from sqlalchemy import text as sql_text

        # Fetch both entities
        keep_sql = sql_text("SELECT * FROM entities WHERE id = :eid")
        merge_sql = sql_text("SELECT * FROM entities WHERE id = :eid")

        keep_row = (await session.execute(keep_sql, {"eid": str(keep_id)})).fetchone()
        merge_row = (await session.execute(merge_sql, {"eid": str(merge_id)})).fetchone()

        if not keep_row or not merge_row:
            return {"error": "One or both entities not found"}

        # Merge payload: merge_entity's payload fills gaps in keep_entity's
        keep_payload = keep_row.payload or {}
        merge_payload = merge_row.payload or {}
        merged_payload = {**merge_payload, **keep_payload}  # keep_entity wins on conflicts

        # Track merge provenance
        merged_payload["_merged_from"] = merged_payload.get("_merged_from", [])
        merged_payload["_merged_from"].append({
            "entity_id": str(merge_id),
            "source_name": merge_row.source_name,
            "source_id": merge_row.source_id,
            "name": merge_row.name,
        })

        # Update kept entity's payload
        await session.execute(
            sql_text("UPDATE entities SET payload = :p WHERE id = :eid"),
            {"p": merged_payload, "eid": str(keep_id)},
        )

        # Redirect knowledge_edges references
        edge_updates = 0
        for col in ["source_id", "target_id"]:
            result = await session.execute(
                sql_text(f"UPDATE knowledge_edges SET {col} = :keep WHERE {col} = :merge"),
                {"keep": str(keep_id), "merge": str(merge_id)},
            )
            edge_updates += result.rowcount

        # Redirect embedding references
        emb_result = await session.execute(
            sql_text("UPDATE embeddings SET source_id = :keep WHERE source_id = :merge"),
            {"keep": str(keep_id), "merge": str(merge_id)},
        )

        # Mark merged entity
        await session.execute(
            sql_text("UPDATE entities SET status = 'merged' WHERE id = :eid"),
            {"eid": str(merge_id)},
        )

        return {
            "kept": str(keep_id),
            "merged": str(merge_id),
            "payload_fields_added": len(merge_payload),
            "edges_redirected": edge_updates,
            "embeddings_redirected": emb_result.rowcount,
        }

    async def auto_resolve(
        self,
        session: AsyncSession,
        entity_type: str | None = None,
        min_confidence: float = 0.95,
        dry_run: bool = True,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Automatically merge high-confidence duplicate pairs.

        Only merges pairs above min_confidence. In dry_run mode (default),
        returns what would be merged without executing.

        Uses ontology-based confidence boosting:
        - Cross-ref ID matches get +0.03 boost (strong structural signal)
        - Country normalization matches get +0.02 boost (ISO code agreement)
        - Same equivalence group sources get +0.02 boost (domain coherence)
        """
        candidates = await self.find_duplicates(session, entity_type=entity_type, limit=limit)

        # Apply ontology-based confidence boosting
        for c in candidates:
            boost = 0.0
            match_type = c.get("match_type", "")

            if match_type == "cross_ref_id":
                boost += 0.03
            elif match_type == "country_normalization":
                boost += 0.02

            src_a = c.get("entity_a_source", "")
            src_b = c.get("entity_b_source", "")
            if _sources_in_same_group(src_a, src_b):
                boost += 0.02

            if boost > 0:
                c["confidence"] = min(1.0, round(c["confidence"] + boost, 4))
                c["ontology_boost"] = round(boost, 4)

        high_conf = [c for c in candidates if c["confidence"] >= min_confidence]

        if dry_run:
            return {
                "mode": "dry_run",
                "candidates": len(candidates),
                "would_merge": len(high_conf),
                "pairs": high_conf,
            }

        merged: list[dict[str, Any]] = []
        for pair in high_conf:
            result = await self.merge_entities(
                session,
                uuid.UUID(pair["entity_a_id"]),
                uuid.UUID(pair["entity_b_id"]),
            )
            merged.append({**pair, "merge_result": result})

        return {
            "mode": "live",
            "candidates": len(candidates),
            "merged": len(merged),
            "results": merged,
        }
