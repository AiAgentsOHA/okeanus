"""Data lineage and provenance tracking.

Records the full ancestry of every record: which source produced it,
which adapter transformed it, which algorithm derived downstream records.
Supports forward (impact) and backward (ancestry) tracing.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.schema.lineage import LineageEdge, LineageNode

logger = logging.getLogger(__name__)


class LineageTracker:
    """Track data provenance through the Okeanus pipeline."""

    async def record_ingestion(
        self,
        session: AsyncSession,
        source_name: str,
        adapter_name: str,
        observation_ids: list[uuid.UUID],
    ) -> uuid.UUID:
        """Record that an adapter produced a set of observations from a source."""
        # Create source node
        source_node = LineageNode(
            node_type="SOURCE",
            name=source_name,
            source_name=source_name,
            payload={"adapter": adapter_name, "observation_count": len(observation_ids)},
        )
        session.add(source_node)
        await session.flush()

        # Create adapter node
        adapter_node = LineageNode(
            node_type="ADAPTER",
            name=adapter_name,
            source_name=source_name,
            transform_name=adapter_name,
        )
        session.add(adapter_node)
        await session.flush()

        # Link source -> adapter
        session.add(LineageEdge(
            parent_id=source_node.id,
            child_id=adapter_node.id,
            edge_type="PRODUCED_BY",
        ))

        # Create observation nodes and link adapter -> observations
        for obs_id in observation_ids:
            obs_node = LineageNode(
                node_type="ENTITY",
                name=f"observation:{obs_id}",
                table_name="observations",
                record_id=obs_id,
                source_name=source_name,
                transform_name=adapter_name,
            )
            session.add(obs_node)
            await session.flush()

            session.add(LineageEdge(
                parent_id=adapter_node.id,
                child_id=obs_node.id,
                edge_type="PRODUCED_BY",
            ))

        await session.flush()
        return adapter_node.id

    async def record_promotion(
        self,
        session: AsyncSession,
        mapper_name: str,
        observation_ids: list[uuid.UUID],
        entity_ids: list[uuid.UUID] | None = None,
        event_ids: list[uuid.UUID] | None = None,
        flow_ids: list[uuid.UUID] | None = None,
        ts_ids: list[uuid.UUID] | None = None,
    ) -> uuid.UUID:
        """Record that a mapper transformed observations into structured records."""
        transform_node = LineageNode(
            node_type="TRANSFORM",
            name=mapper_name,
            transform_name=mapper_name,
            payload={
                "input_count": len(observation_ids),
                "entities": len(entity_ids or []),
                "events": len(event_ids or []),
                "flows": len(flow_ids or []),
                "time_series": len(ts_ids or []),
            },
        )
        session.add(transform_node)
        await session.flush()

        # Link input observations -> transform
        for obs_id in observation_ids:
            # Find existing lineage node for this observation
            stmt = select(LineageNode).where(
                LineageNode.table_name == "observations",
                LineageNode.record_id == obs_id,
            ).limit(1)
            result = await session.execute(stmt)
            obs_node = result.scalar_one_or_none()
            if obs_node:
                session.add(LineageEdge(
                    parent_id=obs_node.id,
                    child_id=transform_node.id,
                    edge_type="CONTRIBUTED_TO",
                ))

        # Create output nodes
        outputs: list[tuple[str, list[uuid.UUID]]] = [
            ("entities", entity_ids or []),
            ("events", event_ids or []),
            ("flows", flow_ids or []),
            ("time_series", ts_ids or []),
        ]
        for table_name, ids in outputs:
            for record_id in ids:
                out_node = LineageNode(
                    node_type="ENTITY",
                    name=f"{table_name}:{record_id}",
                    table_name=table_name,
                    record_id=record_id,
                    transform_name=mapper_name,
                )
                session.add(out_node)
                await session.flush()
                session.add(LineageEdge(
                    parent_id=transform_node.id,
                    child_id=out_node.id,
                    edge_type="DERIVED_FROM",
                ))

        await session.flush()
        return transform_node.id

    async def record_edge_creation(
        self,
        session: AsyncSession,
        algorithm_name: str,
        edge_ids: list[uuid.UUID],
        source_entity_ids: list[uuid.UUID],
    ) -> uuid.UUID:
        """Record that a graph algorithm produced relationship edges."""
        algo_node = LineageNode(
            node_type="TRANSFORM",
            name=algorithm_name,
            transform_name=algorithm_name,
            payload={
                "edges_created": len(edge_ids),
                "source_entities": len(source_entity_ids),
            },
        )
        session.add(algo_node)
        await session.flush()

        # Link source entities -> algorithm
        for eid in source_entity_ids:
            stmt = select(LineageNode).where(
                LineageNode.table_name == "entities",
                LineageNode.record_id == eid,
            ).limit(1)
            result = await session.execute(stmt)
            entity_node = result.scalar_one_or_none()
            if entity_node:
                session.add(LineageEdge(
                    parent_id=entity_node.id,
                    child_id=algo_node.id,
                    edge_type="CONTRIBUTED_TO",
                ))

        # Create edge output nodes
        for rel_id in edge_ids:
            edge_node = LineageNode(
                node_type="EDGE",
                name=f"relationships:{rel_id}",
                table_name="relationships",
                record_id=rel_id,
                transform_name=algorithm_name,
            )
            session.add(edge_node)
            await session.flush()
            session.add(LineageEdge(
                parent_id=algo_node.id,
                child_id=edge_node.id,
                edge_type="PRODUCED_BY",
            ))

        await session.flush()
        return algo_node.id

    async def trace_ancestry(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        table_name: str,
    ) -> dict[str, Any]:
        """Trace full ancestry of a record -- returns DAG of lineage nodes."""
        # Find the lineage node for this record
        stmt = select(LineageNode).where(
            LineageNode.table_name == table_name,
            LineageNode.record_id == record_id,
        ).limit(1)
        result = await session.execute(stmt)
        start_node = result.scalar_one_or_none()

        if not start_node:
            return {"record_id": str(record_id), "table": table_name, "nodes": [], "edges": []}

        # Walk up the DAG via recursive query
        sql = text("""
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id, child_id, edge_type, 0 AS depth
                FROM lineage_edges
                WHERE child_id = :start_id
                UNION ALL
                SELECT e.id, e.parent_id, e.child_id, e.edge_type, a.depth + 1
                FROM lineage_edges e
                JOIN ancestors a ON e.child_id = a.parent_id
                WHERE a.depth < 10
            )
            SELECT DISTINCT parent_id, child_id, edge_type FROM ancestors
        """)
        result = await session.execute(sql, {"start_id": start_node.id})
        edge_rows = result.fetchall()

        # Collect all node IDs
        node_ids = {start_node.id}
        edges_out: list[dict[str, Any]] = []
        for r in edge_rows:
            node_ids.add(r.parent_id)
            node_ids.add(r.child_id)
            edges_out.append({
                "parent_id": str(r.parent_id),
                "child_id": str(r.child_id),
                "edge_type": r.edge_type,
            })

        # Fetch node details
        if node_ids:
            stmt2 = select(LineageNode).where(LineageNode.id.in_(list(node_ids)))
            result2 = await session.execute(stmt2)
            nodes = result2.scalars().all()
        else:
            nodes = []

        nodes_out = [
            {
                "id": str(n.id),
                "node_type": n.node_type,
                "name": n.name,
                "table_name": n.table_name,
                "record_id": str(n.record_id) if n.record_id else None,
                "source_name": n.source_name,
                "transform_name": n.transform_name,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in nodes
        ]

        return {
            "record_id": str(record_id),
            "table": table_name,
            "nodes": nodes_out,
            "edges": edges_out,
        }

    async def trace_impact(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        table_name: str,
    ) -> dict[str, Any]:
        """Trace all downstream dependents of a record."""
        stmt = select(LineageNode).where(
            LineageNode.table_name == table_name,
            LineageNode.record_id == record_id,
        ).limit(1)
        result = await session.execute(stmt)
        start_node = result.scalar_one_or_none()

        if not start_node:
            return {"record_id": str(record_id), "table": table_name, "nodes": [], "edges": []}

        sql = text("""
            WITH RECURSIVE descendants AS (
                SELECT id, parent_id, child_id, edge_type, 0 AS depth
                FROM lineage_edges
                WHERE parent_id = :start_id
                UNION ALL
                SELECT e.id, e.parent_id, e.child_id, e.edge_type, d.depth + 1
                FROM lineage_edges e
                JOIN descendants d ON e.parent_id = d.child_id
                WHERE d.depth < 10
            )
            SELECT DISTINCT parent_id, child_id, edge_type FROM descendants
        """)
        result = await session.execute(sql, {"start_id": start_node.id})
        edge_rows = result.fetchall()

        node_ids = {start_node.id}
        edges_out: list[dict[str, Any]] = []
        for r in edge_rows:
            node_ids.add(r.parent_id)
            node_ids.add(r.child_id)
            edges_out.append({
                "parent_id": str(r.parent_id),
                "child_id": str(r.child_id),
                "edge_type": r.edge_type,
            })

        if node_ids:
            stmt2 = select(LineageNode).where(LineageNode.id.in_(list(node_ids)))
            result2 = await session.execute(stmt2)
            nodes = result2.scalars().all()
        else:
            nodes = []

        nodes_out = [
            {
                "id": str(n.id),
                "node_type": n.node_type,
                "name": n.name,
                "table_name": n.table_name,
                "record_id": str(n.record_id) if n.record_id else None,
                "source_name": n.source_name,
                "transform_name": n.transform_name,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in nodes
        ]

        return {
            "record_id": str(record_id),
            "table": table_name,
            "nodes": nodes_out,
            "edges": edges_out,
        }

    async def source_coverage(
        self,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Summary: which sources produced what outputs."""
        sql = text("""
            SELECT
                n.source_name,
                n.node_type,
                count(*) AS count,
                count(DISTINCT n.table_name) AS table_count,
                min(n.created_at) AS earliest,
                max(n.created_at) AS latest
            FROM lineage_nodes n
            WHERE n.source_name IS NOT NULL
            GROUP BY n.source_name, n.node_type
            ORDER BY count DESC
        """)
        result = await session.execute(sql)
        rows = result.fetchall()

        return [
            {
                "source_name": r.source_name,
                "node_type": r.node_type,
                "count": r.count,
                "table_count": r.table_count,
                "earliest": r.earliest.isoformat() if r.earliest else None,
                "latest": r.latest.isoformat() if r.latest else None,
            }
            for r in rows
        ]
