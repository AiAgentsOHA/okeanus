"""Persist TransformResult into the 7 entity tables with upsert for entities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.schema.economy import (
    Assessment,
    Claim,
    Entity,
    Event,
    Flow,
    Relationship,
    TimeSeries,
)
from okeanus.transform.pipeline import TransformResult, sanitize_geometry


def _prepare_geometry(d: dict) -> None:
    """Sanitize and convert geometry dict to WKB in-place."""
    geom = sanitize_geometry(d.pop("geometry", None))
    if geom is not None:
        try:
            d["geometry"] = from_shape(shape(geom), srid=4326)
        except Exception:
            d["geometry"] = None
    else:
        d["geometry"] = None


def _ensure_id(d: dict) -> None:
    """Ensure the dict has an id field (UUID)."""
    if "id" not in d or d["id"] is None:
        d["id"] = uuid.uuid4()


def _ensure_timestamp(d: dict) -> None:
    """Convert string timestamps to datetime if needed."""
    ts = d.get("timestamp")
    if isinstance(ts, str):
        d["timestamp"] = datetime.fromisoformat(ts)


async def store_transform_result(
    session: AsyncSession,
    result: TransformResult,
) -> dict[str, int]:
    """Persist all TransformResult items into the 7 entity tables.

    Returns {"time_series": N, "entities": N, ...} count dict.
    """
    counts: dict[str, int] = {}

    # --- Entities first (upsert) ---
    if result.entities:
        for d in result.entities:
            _prepare_geometry(d)
            _ensure_timestamp(d)
            _ensure_id(d)

        stmt = insert(Entity).values(result.entities)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_entities_source",
            set_={
                "name": stmt.excluded.name,
                "entity_type": stmt.excluded.entity_type,
                "country": stmt.excluded.country,
                "sector": stmt.excluded.sector,
                "status": stmt.excluded.status,
                "geometry": stmt.excluded.geometry,
                "quality_score": stmt.excluded.quality_score,
                "payload": stmt.excluded.payload,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        await session.execute(stmt)
        counts["entities"] = len(result.entities)

    # --- All other tables (bulk insert) ---
    table_map: list[tuple[str, type, list[dict]]] = [
        ("time_series", TimeSeries, result.time_series),
        ("flows", Flow, result.flows),
        ("events", Event, result.events),
        ("assessments", Assessment, result.assessments),
        ("claims", Claim, result.claims),
        ("relationships", Relationship, result.relationships),
    ]

    for name, model, items in table_map:
        if not items:
            counts[name] = 0
            continue
        for d in items:
            _prepare_geometry(d)
            _ensure_timestamp(d)
            _ensure_id(d)
        await session.execute(insert(model).values(items))
        counts[name] = len(items)

    # -- Intelligence layer: build knowledge graph edges --
    try:
        from okeanus.ml.graph.builder import KnowledgeGraphBuilder
        from okeanus.config import settings
        if settings.graph_auto_build:
            builder = KnowledgeGraphBuilder()
            edge_count = await builder.build_from_transform(result, session)
            if edge_count:
                counts["knowledge_edges"] = edge_count
    except ImportError:
        pass  # ml extras not installed
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Graph builder hook failed: %s", exc)

    return counts
