"""Build knowledge graph edges from transform pipeline output."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.ml.graph.models import EdgeType, KnowledgeEdge, NodeType
from okeanus.schema.economy import Entity, Relationship, TimeSeries
from okeanus.transform.pipeline import TransformResult

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
                    "id": uuid.uuid4(),
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
                    "id": uuid.uuid4(),
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
                            "id": uuid.uuid4(),
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
                    "id": uuid.uuid4(),
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
                    "id": uuid.uuid4(),
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
            await session.execute(insert(KnowledgeEdge).values(edges))
        return len(edges)

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
