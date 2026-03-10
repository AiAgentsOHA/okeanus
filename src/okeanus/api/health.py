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
