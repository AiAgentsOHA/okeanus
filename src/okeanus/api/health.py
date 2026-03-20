"""Health check endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text

from okeanus import __version__
from okeanus.config import settings
from okeanus.db.postgres import engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict:
    """Basic health check."""
    return {"status": "ok", "version": __version__}


@router.get("/stats")
async def stats() -> dict:
    """Live database statistics for the dashboard."""
    try:
        async with engine.connect() as conn:
            entities = (await conn.execute(text("SELECT count(*) FROM entities"))).scalar() or 0
            observations = (await conn.execute(text("SELECT count(*) FROM observations"))).scalar() or 0
            alerts = (await conn.execute(text("SELECT count(*) FROM alerts"))).scalar() or 0
            sources = (await conn.execute(text(
                "SELECT count(DISTINCT source_name) FROM observations"
            ))).scalar() or 0
            edges = (await conn.execute(text("SELECT count(*) FROM knowledge_edges"))).scalar() or 0

            dist_rows = await conn.execute(text(
                "SELECT entity_type, count(*) as count FROM entities "
                "WHERE entity_type IS NOT NULL GROUP BY entity_type ORDER BY count DESC"
            ))
            entity_dist = [{"entity_type": r[0], "count": r[1]} for r in dist_rows.fetchall()]

            sev_rows = await conn.execute(text(
                "SELECT severity, count(*) as count FROM alerts GROUP BY severity ORDER BY count DESC"
            ))
            severity = [{"severity": r[0], "count": r[1]} for r in sev_rows.fetchall()]

            src_rows = await conn.execute(text(
                "SELECT source_name, count(*) as count FROM observations "
                "GROUP BY source_name ORDER BY count DESC LIMIT 20"
            ))
            source_breakdown = [{"source": r[0], "count": r[1]} for r in src_rows.fetchall()]

        return {
            "entities": entities,
            "observations": observations,
            "alerts": alerts,
            "sources": sources,
            "edges": edges,
            "entity_distribution": entity_dist,
            "severity_distribution": severity,
            "source_breakdown": source_breakdown,
        }
    except Exception as exc:
        logger.warning("Stats query failed: %s", exc)
        return {"entities": 0, "observations": 0, "alerts": 0, "sources": 0, "edges": 0,
                "entity_distribution": [], "severity_distribution": [], "source_breakdown": []}


@router.get("/graph")
async def graph_data() -> dict:
    """Knowledge graph nodes and edges for visualization."""
    try:
        async with engine.connect() as conn:
            # Top 200 entities by edge count as nodes
            node_rows = await conn.execute(text("""
                WITH edge_counts AS (
                    SELECT entity_id, count(*) as edges FROM (
                        SELECT source_id as entity_id FROM knowledge_edges
                        UNION ALL
                        SELECT target_id as entity_id FROM knowledge_edges
                    ) sub GROUP BY entity_id ORDER BY edges DESC LIMIT 200
                )
                SELECT e.id, e.name, e.entity_type,
                       ec.edges as centrality,
                       ST_Y(e.geometry::geometry) as lat,
                       ST_X(e.geometry::geometry) as lon
                FROM entities e
                JOIN edge_counts ec ON e.id = ec.entity_id
            """))
            nodes = [{"id": str(r[0]), "name": r[1], "entity_type": r[2],
                       "centrality": r[3], "latitude": r[4], "longitude": r[5]}
                     for r in node_rows.fetchall()]

            node_ids = {n["id"] for n in nodes}

            # Edges between those nodes
            edge_rows = await conn.execute(text("""
                SELECT source_id, target_id, edge_type, strength
                FROM knowledge_edges
                WHERE source_id = ANY(:ids) AND target_id = ANY(:ids)
                LIMIT 1000
            """), {"ids": list(node_ids)})
            edges = [{"source": str(r[0]), "target": str(r[1]),
                       "edge_type": r[2], "weight": float(r[3]) if r[3] else 1.0}
                     for r in edge_rows.fetchall()]

        return {"nodes": nodes, "edges": edges}
    except Exception as exc:
        logger.warning("Graph query failed: %s", exc)
        return {"nodes": [], "edges": []}


@router.get("/entities")
async def entities_list(limit: int = 500) -> list[dict]:
    """Entity list with coordinates for globe view."""
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(text("""
                SELECT id, name, entity_type, source_name,
                       ST_Y(ST_Centroid(geometry)) as lat,
                       ST_X(ST_Centroid(geometry)) as lon
                FROM entities
                WHERE geometry IS NOT NULL
                  AND ST_Y(ST_Centroid(geometry)) BETWEEN -90 AND 90
                ORDER BY random()
                LIMIT :lim
            """), {"lim": limit})
            return [{"id": str(r[0]), "name": r[1], "entity_type": r[2],
                     "source_name": r[3], "latitude": r[4], "longitude": r[5]}
                    for r in rows.fetchall()]
    except Exception as exc:
        logger.warning("Entities query failed: %s", exc)
        return []


@router.get("/sources")
async def health_sources() -> dict:
    """Check connectivity to each configured data source."""
    checks: dict[str, dict] = {}

    # PostgreSQL / PostGIS
    try:
        async with engine.connect() as conn:
            row = await conn.execute(text("SELECT PostGIS_Version()"))
            postgis_version = row.scalar()
        checks["postgres"] = {"status": "ok", "postgis_version": postgis_version}
    except Exception as exc:
        logger.warning("PostgreSQL health check failed: %s", exc)
        checks["postgres"] = {"status": "error", "detail": str(exc)}

    # External sources — report configuration status
    for source in settings.configured_sources():
        key = source["name"].lower().replace(" ", "_")
        if source["configured"]:
            checks[key] = {"status": "configured"}
        else:
            checks[key] = {"status": "not_configured"}

    all_ok = all(
        c.get("status") in ("ok", "configured", "not_configured") for c in checks.values()
    )
    return {
        "status": "ok" if all_ok else "degraded",
        "version": __version__,
        "sources": checks,
    }
