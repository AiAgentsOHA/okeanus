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
