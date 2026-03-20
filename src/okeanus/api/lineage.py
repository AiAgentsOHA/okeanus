"""Data lineage / provenance API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.db.postgres import get_session
from okeanus.ml.lineage import LineageTracker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lineage", tags=["lineage"])

_tracker = LineageTracker()


async def _get_session():
    async with get_session() as session:
        yield session


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
