"""Data lineage / provenance API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.db.postgres import get_session
from okeanus.ml.lineage import LineageTracker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lineage", tags=["lineage"])

_tracker = LineageTracker()


async def _get_session():
    async with get_session() as session:
        yield session


@router.get("/tree/{entity_id}")
async def decision_tree(
    entity_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> dict[str, Any]:
    """Full decision provenance tree for an entity.

    Returns the complete chain: source -> adapter -> entity -> edges -> community -> insight -> reasoning_traces.
    This is the core decision intelligence endpoint.
    """
    tree: dict[str, Any] = {"entity_id": str(entity_id), "layers": []}

    # Layer 1: Entity info
    ent_row = (await session.execute(text("""
        SELECT id, name, entity_type, source_name, sector, country,
               ST_Y(ST_Centroid(geometry::geometry)) as lat,
               ST_X(ST_Centroid(geometry::geometry)) as lon
        FROM entities WHERE id = :eid
    """), {"eid": entity_id})).fetchone()

    if not ent_row:
        return {"entity_id": str(entity_id), "error": "Entity not found", "layers": []}

    tree["entity"] = {
        "id": str(ent_row.id), "name": ent_row.name,
        "entity_type": ent_row.entity_type, "source_name": ent_row.source_name,
        "sector": ent_row.sector, "country": ent_row.country,
        "lat": ent_row.lat, "lon": ent_row.lon,
    }

    # Layer 2: Lineage ancestry (source -> adapter -> entity)
    ancestry = await _tracker.trace_ancestry(session, entity_id, "entities")
    tree["layers"].append({
        "name": "data_lineage",
        "label": "Data Lineage",
        "nodes": ancestry.get("nodes", []),
        "edges": ancestry.get("edges", []),
    })

    # Layer 3: Knowledge graph edges (what connects this entity)
    edge_rows = (await session.execute(text("""
        SELECT id, source_id, target_id, edge_type, strength,
               source_label, target_label, source_type, target_type,
               evidence_type
        FROM knowledge_edges
        WHERE source_id = :eid OR target_id = :eid
        ORDER BY strength DESC NULLS LAST
        LIMIT 50
    """), {"eid": entity_id})).fetchall()

    tree["layers"].append({
        "name": "knowledge_graph",
        "label": "Knowledge Graph Connections",
        "edges": [
            {
                "id": str(r.id), "source_id": str(r.source_id),
                "target_id": str(r.target_id), "edge_type": r.edge_type,
                "strength": r.strength, "source_label": r.source_label,
                "target_label": r.target_label, "evidence_type": r.evidence_type,
            }
            for r in edge_rows
        ],
        "count": len(edge_rows),
    })

    # Layer 4: Community membership (from NetworkX in-memory engine)
    community_info = None
    try:
        from okeanus.ml.graph.networkx_engine import get_engine
        engine = get_engine()
        if engine.is_stale:
            await engine.ensure_built(session)
        metrics = engine._metrics
        community_id = metrics.get("community", {}).get(str(entity_id))
        if community_id is not None:
            community_size = metrics.get("community_sizes", {}).get(community_id, 0)
            community_info = {
                "community_id": community_id,
                "size": community_size,
                "pagerank": metrics.get("pagerank", {}).get(str(entity_id)),
                "centrality": metrics.get("degree_centrality", {}).get(str(entity_id)),
            }
    except Exception:
        pass

    tree["layers"].append({
        "name": "community",
        "label": "Community Membership",
        "community": community_info,
    })

    # Layer 5: Insights linked to this entity's community or matching its domain
    insight_rows = []

    # First try: match by community_id in generator or evidence
    if community_info and community_info.get("community_id") is not None:
        cid = community_info["community_id"]
        insight_rows = (await session.execute(text("""
            SELECT id, insight_type, title, description, confidence, generator,
                   evidence, involved_domains, status, created_at
            FROM insights
            WHERE generator ILIKE :gen_pattern
               OR (evidence->>'community_id')::int = :cid
            ORDER BY confidence DESC
            LIMIT 20
        """), {"gen_pattern": f"%community-{cid}%", "cid": cid})).fetchall()

    # Fallback: match by entity_type in involved_domains
    if not insight_rows and ent_row.entity_type:
        insight_rows = (await session.execute(text("""
            SELECT id, insight_type, title, description, confidence, generator,
                   evidence, involved_domains, status, created_at
            FROM insights
            WHERE :etype = ANY(involved_domains)
            ORDER BY confidence DESC
            LIMIT 10
        """), {"etype": ent_row.entity_type})).fetchall()

    insights_out = []
    for r in insight_rows:
        # Fetch reasoning traces for this insight
        traces = (await session.execute(text("""
            SELECT id, phase, input_text, output_text, created_at
            FROM reasoning_traces
            WHERE insight_id = :iid
            ORDER BY created_at
        """), {"iid": r.id})).fetchall()

        insights_out.append({
            "id": str(r.id), "insight_type": r.insight_type,
            "title": r.title, "description": r.description[:500],
            "confidence": r.confidence, "generator": r.generator,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reasoning_traces": [
                {
                    "id": str(t.id), "phase": t.phase,
                    "input_text": t.input_text[:500],
                    "output_text": t.output_text[:500],
                }
                for t in traces
            ],
        })

    tree["layers"].append({
        "name": "insights",
        "label": "Generated Insights",
        "insights": insights_out,
        "count": len(insights_out),
    })

    return tree


@router.get("/{table}/{record_id}")
async def trace_ancestry(
    table: str,
    record_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> dict[str, Any]:
    """Trace full ancestry of a record."""
    return await _tracker.trace_ancestry(session, record_id, table)


@router.get("/impact/{table}/{record_id}")
async def trace_impact(
    table: str,
    record_id: uuid.UUID,
    session: AsyncSession = Depends(_get_session),
) -> dict[str, Any]:
    """Trace all downstream dependents of a record."""
    return await _tracker.trace_impact(session, record_id, table)


@router.get("/sources")
async def source_coverage(
    session: AsyncSession = Depends(_get_session),
) -> list[dict[str, Any]]:
    """Source coverage summary -- which sources produced what outputs."""
    return await _tracker.source_coverage(session)
