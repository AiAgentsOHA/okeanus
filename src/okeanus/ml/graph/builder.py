"""Build knowledge graph edges from transform pipeline output."""

from __future__ import annotations

import logging
import uuid as _uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.ml.graph.models import EdgeType, KnowledgeEdge, NodeType
from okeanus.schema.economy import Entity, Relationship, TimeSeries
from okeanus.transform.pipeline import TransformResult

OKEANUS_NS = _uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890')

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """Constructs knowledge-graph edges from structured data."""

    async def build_from_transform(
        self,
        result: TransformResult,
        session: AsyncSession,
    ) -> int:
        """After adapter data is stored, create edges.

        1. Entity-Entity edges from explicit Relationships in the result
        2. Entity-TimeSeries edges (entity produces/has timeseries)
        3. Temporal co-occurrence edges (CO_OCCURS) for same-timeframe events
        """
        total = 0
        edges: list[dict[str, Any]] = []

        # 1. Relationships -> edges
        for rel in result.relationships:
            src_id = rel.get("source_entity_id")
            dst_id = rel.get("dest_entity_id")
            if not src_id or not dst_id:
                continue
            edge_type = self._map_rel_type(rel.get("relationship_type", "RELATES_TO"))
            edges.append(
                {
                    "id": _uuid.uuid4(),
                    "source_id": src_id,
                    "source_type": NodeType.ENTITY.value,
                    "source_label": None,
                    "target_id": dst_id,
                    "target_type": NodeType.ENTITY.value,
                    "target_label": None,
                    "edge_type": edge_type,
                    "strength": rel.get("strength", 1.0) or 1.0,
                    "evidence_type": "adapter_data",
                    "evidence_detail": rel.get("source_name"),
                    "domain": None,
                    "payload": rel.get("payload"),
                }
            )

        # 2. Entity-TimeSeries edges
        for ts in result.time_series:
            entity_id = ts.get("entity_id")
            ts_id = ts.get("id")
            if not entity_id or not ts_id:
                continue
            edges.append(
                {
                    "id": _uuid.uuid4(),
                    "source_id": entity_id,
                    "source_type": NodeType.ENTITY.value,
                    "source_label": None,
                    "target_id": ts_id,
                    "target_type": NodeType.TIMESERIES.value,
                    "target_label": ts.get("code"),
                    "edge_type": EdgeType.RELATES_TO.value,
                    "strength": 1.0,
                    "evidence_type": "adapter_data",
                    "evidence_detail": ts.get("source_name"),
                    "domain": None,
                    "payload": None,
                }
            )

        # 3. Temporal co-occurrence edges for events
        events_with_entity = [
            e for e in result.events if e.get("entity_id") and e.get("id")
        ]
        if len(events_with_entity) >= 2:
            for i, ev_a in enumerate(events_with_entity):
                for ev_b in events_with_entity[i + 1 :]:
                    if ev_a.get("entity_id") == ev_b.get("entity_id"):
                        continue
                    edges.append(
                        {
                            "id": _uuid.uuid4(),
                            "source_id": ev_a["id"],
                            "source_type": NodeType.EVENT.value,
                            "source_label": ev_a.get("name"),
                            "target_id": ev_b["id"],
                            "target_type": NodeType.EVENT.value,
                            "target_label": ev_b.get("name"),
                            "edge_type": EdgeType.CO_OCCURS.value,
                            "strength": 0.5,
                            "evidence_type": "temporal_cooccurrence",
                            "evidence_detail": None,
                            "domain": None,
                            "payload": None,
                        }
                    )

        if edges:
            await session.execute(insert(KnowledgeEdge).values(edges))
            total = len(edges)

        return total

    async def sync_from_relationships(self, session: AsyncSession) -> int:
        """Migrate existing ``relationships`` table entries into knowledge_edges.

        Reads from :class:`okeanus.schema.economy.Relationship`, maps
        ``relationship_type`` to :class:`EdgeType`, copies ``strength``,
        and sets ``evidence_type='adapter_data'``.
        """
        result = await session.execute(select(Relationship))
        rels = result.scalars().all()
        if not rels:
            return 0

        edges: list[dict[str, Any]] = []
        for rel in rels:
            edge_type = self._map_rel_type(rel.relationship_type)
            edges.append(
                {
                    "id": _uuid.uuid4(),
                    "source_id": rel.source_entity_id,
                    "source_type": NodeType.ENTITY.value,
                    "source_label": None,
                    "target_id": rel.dest_entity_id,
                    "target_type": NodeType.ENTITY.value,
                    "target_label": None,
                    "edge_type": edge_type,
                    "strength": rel.strength if rel.strength is not None else 1.0,
                    "evidence_type": "adapter_data",
                    "evidence_detail": rel.source_name,
                    "domain": None,
                    "payload": rel.payload,
                }
            )

        if edges:
            await session.execute(insert(KnowledgeEdge).values(edges))
        return len(edges)

    async def build_spatial_edges(
        self,
        session: AsyncSession,
        radius_km: float = 50.0,
    ) -> int:
        """Find entities with geometry within *radius_km* of each other.

        Uses PostGIS ``ST_DWithin`` (in degrees, approximate: radius_km / 111.0).
        Creates ``SPATIALLY_NEAR`` edges with strength inversely proportional to
        distance.  Only creates edges between different entity types or different
        sources to keep the graph informative.
        """
        degree_radius = radius_km / 111.0

        sql = text(
            """
            SELECT
                a.id   AS a_id,
                a.entity_type AS a_type,
                a.name AS a_name,
                a.source_name AS a_source,
                b.id   AS b_id,
                b.entity_type AS b_type,
                b.name AS b_name,
                b.source_name AS b_source,
                ST_Distance(a.geometry, b.geometry) * 111.0 AS dist_km
            FROM entities a
            JOIN entities b
              ON a.id < b.id
              AND ST_DWithin(a.geometry, b.geometry, :radius)
            WHERE a.geometry IS NOT NULL
              AND b.geometry IS NOT NULL
              AND (a.entity_type != b.entity_type OR a.source_name != b.source_name)
            LIMIT 5000
            """
        )
        rows = (await session.execute(sql, {"radius": degree_radius})).fetchall()
        if not rows:
            return 0

        edges: list[dict[str, Any]] = []
        for row in rows:
            dist_km = row.dist_km if row.dist_km else 0.0
            strength = max(0.1, 1.0 - (dist_km / radius_km))
            edges.append(
                {
                    "id": _uuid.uuid4(),
                    "source_id": row.a_id,
                    "source_type": NodeType.ENTITY.value,
                    "source_label": row.a_name,
                    "target_id": row.b_id,
                    "target_type": NodeType.ENTITY.value,
                    "target_label": row.b_name,
                    "edge_type": EdgeType.SPATIALLY_NEAR.value,
                    "strength": round(strength, 4),
                    "evidence_type": "spatial_proximity",
                    "evidence_detail": f"{dist_km:.1f}km",
                    "domain": None,
                    "payload": None,
                }
            )

        if edges:
            # Batch inserts to stay under asyncpg's 32767 parameter limit
            # Each edge has 13 columns, so max ~2500 per batch
            batch_size = 2000
            for i in range(0, len(edges), batch_size):
                await session.execute(
                    insert(KnowledgeEdge).values(edges[i : i + batch_size])
                )
        return len(edges)

    # ------------------------------------------------------------------
    # Semantic similarity edges from embeddings
    # ------------------------------------------------------------------

    async def build_semantic_edges(
        self,
        session: AsyncSession,
        min_similarity: float = 0.5,
        max_edges: int = 5000,
        neighbors_per_row: int = 10,
    ) -> int:
        """Create edges between entities with similar embeddings.

        Uses pgvector IVFFlat index via LATERAL nearest-neighbor lookup
        instead of a brute-force cross-join.  For each distinct pair of
        source_types, the *smaller* side drives a lateral scan into the
        larger side.  Deduplication is done in Python to keep the SQL
        simple and fast.
        """
        # 1. Discover source_types with counts (drive from smaller side)
        type_rows = (await session.execute(
            text("""SELECT source_type, count(*) AS cnt
                    FROM embeddings GROUP BY source_type ORDER BY cnt""")
        )).fetchall()
        type_counts = [(r[0], r[1]) for r in type_rows]

        if len(type_counts) < 2:
            logger.info("Fewer than 2 source_types — no cross-type edges possible")
            return 0

        # 2. For every source_type pair, lateral NN from smaller into larger
        all_rows: list[Any] = []
        seen_pairs: set[tuple[str, str]] = set()

        for i, (st_a, cnt_a) in enumerate(type_counts):
            for st_b, cnt_b in type_counts[i + 1:]:
                if len(all_rows) >= max_edges:
                    break

                # Always scan from the smaller side
                if cnt_a <= cnt_b:
                    probe_type, target_type = st_a, st_b
                else:
                    probe_type, target_type = st_b, st_a

                remaining = max_edges - len(all_rows)
                sql = text("""
                    SELECT
                        a.source_id    AS a_id,
                        a.source_type  AS a_type,
                        a.text_content AS a_text,
                        nb.source_id   AS b_id,
                        nb.source_type AS b_type,
                        nb.text_content AS b_text,
                        1 - (a.embedding <=> nb.embedding) AS similarity
                    FROM embeddings a
                    CROSS JOIN LATERAL (
                        SELECT b.source_id, b.source_type, b.text_content, b.embedding
                        FROM embeddings b
                        WHERE b.source_type = :target_type
                        ORDER BY b.embedding <=> a.embedding
                        LIMIT :k
                    ) nb
                    WHERE a.source_type = :probe_type
                      AND 1 - (a.embedding <=> nb.embedding) >= :min_sim
                    LIMIT :lim
                """)
                rows = (await session.execute(sql, {
                    "probe_type": probe_type,
                    "target_type": target_type,
                    "k": neighbors_per_row,
                    "min_sim": min_similarity,
                    "lim": remaining,
                })).fetchall()

                for row in rows:
                    pair_key = (str(min(row.a_id, row.b_id)),
                                str(max(row.a_id, row.b_id)))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        all_rows.append(row)

                logger.info(
                    "Semantic edges %s<->%s: %d candidates (probe=%s, %d rows)",
                    st_a, st_b, len(rows), probe_type,
                    cnt_a if probe_type == st_a else cnt_b,
                )

        if not all_rows:
            return 0

        # 3. Build edge dicts
        edges: list[dict[str, Any]] = []
        for row in all_rows:
            similarity = float(row.similarity)
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": row.a_id,
                "source_type": row.a_type,
                "source_label": (row.a_text[:100] if row.a_text else None),
                "target_id": row.b_id,
                "target_type": row.b_type,
                "target_label": (row.b_text[:100] if row.b_text else None),
                "edge_type": EdgeType.RELATES_TO.value,
                "strength": round(similarity, 4),
                "evidence_type": "semantic_similarity",
                "evidence_detail": f"cosine_sim={similarity:.4f}",
                "domain": None,
                "payload": None,
            })

        if edges:
            batch_size = 2000
            for i in range(0, len(edges), batch_size):
                await session.execute(
                    insert(KnowledgeEdge).values(edges[i : i + batch_size])
                )
        logger.info("Created %d semantic similarity edges", len(edges))
        return len(edges)

    # ------------------------------------------------------------------
    # Correlation-discovered edges
    # ------------------------------------------------------------------

    async def build_correlation_edges(
        self,
        session: AsyncSession,
        correlations: list[dict[str, Any]],
    ) -> int:
        """Create CORRELATES_WITH edges from correlator discoveries.

        Each correlation result should have code_a, code_b, and statistical
        evidence (correlation, p_value, lag_days, method).
        """
        if not correlations:
            return 0

        # Look up entity IDs for time series codes
        codes = set()
        for c in correlations:
            ev = c.get("evidence", c)
            codes.add(ev.get("code_a", ""))
            codes.add(ev.get("code_b", ""))
        codes.discard("")

        if not codes:
            return 0

        # Map time series codes -> time_series UUID primary keys
        placeholders = ", ".join(f":c{i}" for i in range(len(codes)))
        code_list = list(codes)
        params = {f"c{i}": code for i, code in enumerate(code_list)}
        sql = text(f"""
            SELECT DISTINCT ON (code) code, id AS ts_id, name AS ts_name
            FROM time_series
            WHERE code IN ({placeholders})
            ORDER BY code, timestamp DESC
        """)
        rows = (await session.execute(sql, params)).fetchall()

        code_to_node: dict[str, tuple[_uuid.UUID, str]] = {}
        for row in rows:
            code_to_node[row.code] = (row.ts_id, NodeType.TIMESERIES.value)

        edges: list[dict[str, Any]] = []
        for c in correlations:
            ev = c.get("evidence", c)
            code_a = ev.get("code_a", "")
            code_b = ev.get("code_b", "")
            node_a = code_to_node.get(code_a)
            node_b = code_to_node.get(code_b)

            if not node_a or not node_b or node_a[0] == node_b[0]:
                continue

            corr_val = ev.get("correlation", 0)
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": node_a[0],
                "source_type": node_a[1],
                "source_label": code_a,
                "target_id": node_b[0],
                "target_type": node_b[1],
                "target_label": code_b,
                "edge_type": EdgeType.CORRELATES_WITH.value,
                "strength": round(abs(corr_val), 4),
                "evidence_type": "statistical_correlation",
                "evidence_detail": (
                    f"r={corr_val}, p={ev.get('p_value', 'N/A')}, "
                    f"lag={ev.get('lag_days', 0)}d, method={ev.get('method', 'pearson')}"
                ),
                "domain": None,
                "payload": {
                    "correlation": corr_val,
                    "p_value": ev.get("p_value"),
                    "lag_days": ev.get("lag_days", 0),
                    "method": ev.get("method", "pearson"),
                    "n_points": ev.get("n_points"),
                },
            })

        if edges:
            await session.execute(insert(KnowledgeEdge).values(edges))
        logger.info("Created %d correlation edges", len(edges))
        return len(edges)

    # ------------------------------------------------------------------
    # Batch insert helper
    # ------------------------------------------------------------------

    async def _batch_insert_edges(
        self, session: AsyncSession, edges: list[dict[str, Any]]
    ) -> int:
        """Insert edges in batches with ON CONFLICT DO NOTHING."""
        if not edges:
            return 0
        batch_size = 2000
        for i in range(0, len(edges), batch_size):
            stmt = insert(KnowledgeEdge).values(edges[i : i + batch_size])
            stmt = stmt.on_conflict_do_nothing()
            await session.execute(stmt)
        return len(edges)

    # ------------------------------------------------------------------
    # Domain-aware edge builders
    # ------------------------------------------------------------------

    async def build_mmsi_edges(self, session: AsyncSession) -> int:
        """Link entities sharing the same MMSI (vessel identity).

        Handles double-nested payload (payload->'payload'->>'mmsi') and
        AISStream identifiers (ais-{MMSI}-{timestamp}).
        """
        sql = text("""
            WITH mmsi_entities AS (
                SELECT id, name, source_name,
                       COALESCE(
                           payload->'payload'->>'mmsi',
                           CASE WHEN source_name = 'AISStream'
                                     AND identifier LIKE 'ais-%%'
                                THEN split_part(identifier, '-', 2)
                           END
                       ) as mmsi
                FROM entities
                WHERE payload->'payload'->>'mmsi' IS NOT NULL
                   OR (source_name = 'AISStream' AND identifier LIKE 'ais-%%')
            )
            SELECT DISTINCT a.id, a.name, b.id, b.name
            FROM mmsi_entities a
            JOIN mmsi_entities b ON a.id < b.id
            WHERE a.mmsi = b.mmsi AND a.mmsi != ''
              AND a.source_name != b.source_name
            LIMIT 10000
        """)
        rows = (await session.execute(sql)).fetchall()
        if not rows:
            return 0
        edges = []
        for r in rows:
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": r[0], "source_type": NodeType.ENTITY.value,
                "source_label": r[1],
                "target_id": r[2], "target_type": NodeType.ENTITY.value,
                "target_label": r[3],
                "edge_type": EdgeType.IDENTITY.value,
                "strength": 1.0,
                "evidence_type": "mmsi_identity",
                "evidence_detail": None, "domain": None, "payload": None,
            })
        return await self._batch_insert_edges(session, edges)

    async def build_aphia_edges(self, session: AsyncSession) -> int:
        """Link entities sharing same AphiaID (species taxonomy).

        Payload is double-nested: payload->'payload'->>'aphia_id'.
        """
        sql = text("""
            SELECT DISTINCT a.id, a.name, b.id, b.name
            FROM entities a JOIN entities b ON a.id < b.id
            WHERE (a.payload->'payload'->>'aphia_id') IS NOT NULL
              AND (a.payload->'payload'->>'aphia_id') = (b.payload->'payload'->>'aphia_id')
              AND a.source_name != b.source_name
            LIMIT 7000
        """)
        rows = (await session.execute(sql)).fetchall()
        if not rows:
            return 0
        edges = []
        for r in rows:
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": r[0], "source_type": NodeType.ENTITY.value,
                "source_label": r[1],
                "target_id": r[2], "target_type": NodeType.ENTITY.value,
                "target_label": r[3],
                "edge_type": EdgeType.IS_A.value,
                "strength": 1.0,
                "evidence_type": "taxonomy_identity",
                "evidence_detail": None, "domain": None, "payload": None,
            })
        return await self._batch_insert_edges(session, edges)

    async def build_country_edges(self, session: AsyncSession) -> int:
        """Link entities in same country but different entity_type or source.

        Uses COALESCE to check both the country column and the nested
        payload->'payload'->>'country' (which has 7K+ entries vs 100).
        """
        sql = text("""
            WITH country_entities AS (
                SELECT id, name, entity_type, source_name,
                       COALESCE(
                           NULLIF(country, ''),
                           payload->'payload'->>'country'
                       ) as resolved_country
                FROM entities
                WHERE country IS NOT NULL AND country != ''
                   OR payload->'payload'->>'country' IS NOT NULL
            )
            SELECT src_id, src_name, tgt_id, tgt_name, resolved_country FROM (
                SELECT a.id as src_id, a.name as src_name,
                       b.id as tgt_id, b.name as tgt_name, a.resolved_country,
                       ROW_NUMBER() OVER (PARTITION BY a.resolved_country) as rn
                FROM country_entities a JOIN country_entities b ON a.id < b.id
                WHERE a.resolved_country IS NOT NULL AND a.resolved_country != ''
                  AND a.resolved_country = b.resolved_country
                  AND (a.entity_type != b.entity_type OR a.source_name != b.source_name)
            ) sub
            WHERE rn <= 50
            LIMIT 30000
        """)
        rows = (await session.execute(sql)).fetchall()
        if not rows:
            return 0
        edges = []
        for r in rows:
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": r[0], "source_type": NodeType.ENTITY.value,
                "source_label": r[1],
                "target_id": r[2], "target_type": NodeType.ENTITY.value,
                "target_label": r[3],
                "edge_type": EdgeType.OPERATES_IN.value,
                "strength": 0.7,
                "evidence_type": "same_country",
                "evidence_detail": r[4], "domain": None, "payload": None,
            })
        return await self._batch_insert_edges(session, edges)

    async def build_sector_edges(self, session: AsyncSession) -> int:
        """Link entities in same sector but different source."""
        sql = text("""
            SELECT a.id, a.name, b.id, b.name
            FROM entities a JOIN entities b ON a.id < b.id
            WHERE a.sector IS NOT NULL AND a.sector != ''
              AND a.sector = b.sector
              AND a.source_name != b.source_name
            LIMIT 8000
        """)
        rows = (await session.execute(sql)).fetchall()
        if not rows:
            return 0
        edges = []
        for r in rows:
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": r[0], "source_type": NodeType.ENTITY.value,
                "source_label": r[1],
                "target_id": r[2], "target_type": NodeType.ENTITY.value,
                "target_label": r[3],
                "edge_type": EdgeType.RELATES_TO.value,
                "strength": 0.6,
                "evidence_type": "same_sector",
                "evidence_detail": None, "domain": None, "payload": None,
            })
        return await self._batch_insert_edges(session, edges)

    async def build_regulatory_edges(self, session: AsyncSession) -> int:
        """Cross-reference regulatory/sanctions entities with vessel entities.

        Handles double-nested payload and AISStream identifier-encoded MMSI.
        """
        sql = text("""
            SELECT s.id as sanction_id, s.name as sanction_name,
                   v.id as vessel_id, v.name as vessel_name
            FROM entities s
            JOIN entities v ON s.id != v.id
            WHERE s.source_name IN ('OFAC SDN', 'OpenSanctions', 'CLAV IUU', 'IUU Fishing Index')
              AND v.source_name IN ('AISStream', 'World Port Index', 'Global Fishing Watch')
              AND (
                (s.payload->'payload'->>'mmsi' IS NOT NULL
                 AND (s.payload->'payload'->>'mmsi' = v.payload->'payload'->>'mmsi'
                      OR (v.source_name = 'AISStream'
                          AND v.identifier LIKE 'ais-%%'
                          AND s.payload->'payload'->>'mmsi' = split_part(v.identifier, '-', 2))))
                OR (s.payload->'payload'->>'imo' IS NOT NULL
                    AND s.payload->'payload'->>'imo' = v.payload->'payload'->>'imo')
              )
            LIMIT 2000
        """)
        rows = (await session.execute(sql)).fetchall()
        if not rows:
            return 0
        edges = []
        for r in rows:
            edges.append({
                "id": _uuid.uuid4(),
                "source_id": r[2], "source_type": NodeType.ENTITY.value,
                "source_label": r[3],
                "target_id": r[0], "target_type": NodeType.ENTITY.value,
                "target_label": r[1],
                "edge_type": EdgeType.REGULATED_BY.value,
                "strength": 0.9,
                "evidence_type": "regulatory_match",
                "evidence_detail": None, "domain": None, "payload": None,
            })
        return await self._batch_insert_edges(session, edges)

    async def build_source_provenance_edges(self, session: AsyncSession) -> int:
        """Create edges linking entities to their source adapter."""
        sources = await session.execute(text(
            "SELECT DISTINCT source_name FROM entities WHERE source_name IS NOT NULL"
        ))
        total = 0
        for (source_name,) in sources.fetchall():
            source_node_id = _uuid.uuid5(OKEANUS_NS, source_name)
            entities = await session.execute(text(
                "SELECT id, name FROM entities WHERE source_name = :sn LIMIT 500"
            ), {"sn": source_name})
            edges = []
            for r in entities.fetchall():
                edges.append({
                    "id": _uuid.uuid4(),
                    "source_id": r[0], "source_type": "entity",
                    "source_label": r[1],
                    "target_id": source_node_id, "target_type": "entity",
                    "target_label": source_name,
                    "edge_type": EdgeType.SOURCED_FROM.value,
                    "strength": 0.5,
                    "evidence_type": "source_provenance",
                    "evidence_detail": source_name, "domain": None, "payload": None,
                })
            total += await self._batch_insert_edges(session, edges)
        return total

    # ------------------------------------------------------------------
    # One-shot backfill pipeline
    # ------------------------------------------------------------------

    async def backfill_all(
        self,
        session: AsyncSession,
        run_correlations: bool = True,
    ) -> dict[str, int]:
        """Run the full graph backfill pipeline.

        1. sync_from_relationships() — migrate existing relationships table
        2. build_spatial_edges() — entities within 50km
        3. build_semantic_edges() — entities with similar embeddings
        4. Run correlator auto-discovery + create correlation edges (optional)
        """
        counts: dict[str, int] = {}

        # 1. Relationships
        try:
            counts["relationships"] = await self.sync_from_relationships(session)
            await session.commit()
            logger.info("Backfill: %d relationship edges", counts["relationships"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill relationships failed: %s", exc)
            counts["relationships"] = 0

        # 2. Spatial edges
        try:
            counts["spatial"] = await self.build_spatial_edges(session)
            await session.commit()
            logger.info("Backfill: %d spatial edges", counts["spatial"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill spatial failed: %s", exc)
            counts["spatial"] = 0

        # 3. MMSI identity edges
        try:
            counts["mmsi"] = await self.build_mmsi_edges(session)
            await session.commit()
            logger.info("Backfill: %d MMSI edges", counts["mmsi"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill MMSI failed: %s", exc)
            counts["mmsi"] = 0

        # 4. AphiaID taxonomy edges
        try:
            counts["aphia"] = await self.build_aphia_edges(session)
            await session.commit()
            logger.info("Backfill: %d Aphia edges", counts["aphia"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill Aphia failed: %s", exc)
            counts["aphia"] = 0

        # 5. Country edges
        try:
            counts["country"] = await self.build_country_edges(session)
            await session.commit()
            logger.info("Backfill: %d country edges", counts["country"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill country failed: %s", exc)
            counts["country"] = 0

        # 6. Sector edges
        try:
            counts["sector"] = await self.build_sector_edges(session)
            await session.commit()
            logger.info("Backfill: %d sector edges", counts["sector"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill sector failed: %s", exc)
            counts["sector"] = 0

        # 7. Regulatory edges
        try:
            counts["regulatory"] = await self.build_regulatory_edges(session)
            await session.commit()
            logger.info("Backfill: %d regulatory edges", counts["regulatory"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill regulatory failed: %s", exc)
            counts["regulatory"] = 0

        # 8. Source provenance edges
        try:
            counts["provenance"] = await self.build_source_provenance_edges(session)
            await session.commit()
            logger.info("Backfill: %d provenance edges", counts["provenance"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill provenance failed: %s", exc)
            counts["provenance"] = 0

        # 9. Semantic similarity edges
        try:
            counts["semantic"] = await self.build_semantic_edges(session)
            await session.commit()
            logger.info("Backfill: %d semantic edges", counts["semantic"])
        except Exception as exc:
            await session.rollback()
            logger.warning("Backfill semantic failed: %s", exc)
            counts["semantic"] = 0

        # 10. Correlation-discovered edges
        if run_correlations:
            try:
                from okeanus.ml.synthesis.correlator import CorrelationEngine
                engine = CorrelationEngine()
                scan_results = await engine.full_scan(session)
                temporal = [
                    r for r in scan_results
                    if r.get("correlation_type") == "temporal"
                ]
                counts["correlation"] = await self.build_correlation_edges(
                    session, temporal,
                )
                await session.commit()
                logger.info("Backfill: %d correlation edges", counts["correlation"])
            except Exception as exc:
                await session.rollback()
                logger.warning("Backfill correlations failed: %s", exc)
                counts["correlation"] = 0

        counts["total"] = sum(counts.values())
        logger.info("Backfill complete: %d total edges", counts["total"])
        return counts

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_rel_type(rel_type: str) -> str:
        """Best-effort mapping from relationship_type strings to EdgeType values."""
        mapping: dict[str, str] = {
            "operates": EdgeType.RELATES_TO.value,
            "invests_in": EdgeType.INFLUENCES.value,
            "regulates": EdgeType.INFLUENCES.value,
            "owns": EdgeType.RELATES_TO.value,
            "supplies": EdgeType.RELATES_TO.value,
            "partners_with": EdgeType.RELATES_TO.value,
            "is_a": EdgeType.IS_A.value,
            "causes": EdgeType.CAUSES.value,
            "contradicts": EdgeType.CONTRADICTS.value,
            "precedes": EdgeType.PRECEDES.value,
            "correlates_with": EdgeType.CORRELATES_WITH.value,
        }
        normalised = rel_type.lower().replace("-", "_").replace(" ", "_")
        # Direct enum match
        for member in EdgeType:
            if normalised == member.value.lower():
                return member.value
        return mapping.get(normalised, EdgeType.RELATES_TO.value)
