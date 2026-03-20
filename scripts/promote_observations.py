"""Promote raw observations into structured economy tables + knowledge graph.

Reads ALL observations from PostgreSQL, routes them through the mapper
registry (30 mappers in transform/mappers.py + 12 in batch_ingest.py),
applies a generic mapper for unmapped sources, and persists results.

Usage:
    .venv/bin/python3 scripts/promote_observations.py
    .venv/bin/python3 scripts/promote_observations.py --dry-run
"""

from __future__ import annotations

import asyncio
import argparse
import logging
import uuid
from datetime import datetime, timezone

from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Register all mappers (30 from mappers.py + 12 from batch_ingest.py)
import importlib.util
import sys
from pathlib import Path

import okeanus.transform.mappers  # noqa: F401

# batch_ingest.py is a script (not a package module), so load it directly
_bi_path = Path(__file__).resolve().parent / "batch_ingest.py"
_bi_spec = importlib.util.spec_from_file_location("batch_ingest", _bi_path)
_bi_mod = importlib.util.module_from_spec(_bi_spec)
sys.modules["batch_ingest"] = _bi_mod
_bi_spec.loader.exec_module(_bi_mod)  # registers 12 more mappers

from okeanus.adapters.esvd import EsvdAdapter
from okeanus.db.postgres import get_session, async_session_factory
from okeanus.schema.economy import (
    Assessment,
    Claim,
    Entity,
    Event,
    Flow,
    Relationship,
    TimeSeries,
)
from okeanus.transform.pipeline import (
    MAPPER_REGISTRY,
    TransformResult,
    entity_uuid,
    register_mapper,
    transform,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("promote")

BATCH_SIZE = 2000


# ===================================================================
# Geometry helper (same as batch_ingest.py)
# ===================================================================

def _geojson_to_wkb(geom: dict | None):
    if geom is None:
        return None
    try:
        return from_shape(shape(geom), srid=4326)
    except Exception:
        return None


# ===================================================================
# Generic mapper for unmapped sources
# ===================================================================

def _generic_mapper(records: list[dict]) -> TransformResult:
    """Create an entity from each observation for sources without a mapper."""
    entities = []
    for rec in records:
        payload = rec.get("payload", {})
        source_name = rec.get("source_name", "unknown")
        source_id = rec.get("source_id", str(uuid.uuid4()))

        # Try to extract a name from payload
        name = (
            payload.get("name")
            or payload.get("title")
            or payload.get("station_name")
            or payload.get("scientific_name")
            or payload.get("species")
            or payload.get("vesselname")
            or f"{source_name} #{source_id[:20]}"
        )

        eid = entity_uuid(source_name, source_id)
        obs_type = rec.get("obs_type", "observation")

        entities.append({
            "id": eid,
            "source_name": source_name,
            "source_id": str(eid),
            "quality_score": rec.get("quality_score"),
            "geometry": rec.get("geometry"),
            "entity_type": obs_type,
            "name": str(name)[:255],
            "identifier": source_id[:255],
            "country": payload.get("country"),
            "sector": None,
            "status": None,
            "payload": payload,
        })
    return TransformResult(entities=entities)


# ===================================================================
# Persist results (extended from batch_ingest.py to cover all tables)
# ===================================================================

async def _persist_results(session, result: TransformResult) -> dict[str, int]:
    """Upsert transformed records into economy tables."""
    counts = {
        "entities": 0, "time_series": 0, "events": 0,
        "flows": 0, "assessments": 0, "claims": 0, "relationships": 0,
    }

    # -- Entities (must go first — FKs depend on them) --
    for rec in result.entities:
        ent_id = rec.pop("id", None) or uuid.uuid4()
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        country_val = rec.get("country")
        if country_val and len(country_val) > 10:
            country_val = country_val[:10]
        stmt = pg_insert(Entity).values(
            id=ent_id,
            source_name=rec.get("source_name", "")[:100],
            source_id=rec.get("source_id", str(ent_id))[:255],
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            entity_type=rec.get("entity_type", "unknown")[:50],
            name=rec.get("name", "Unknown")[:255],
            identifier=(rec.get("identifier") or "")[:255] or None,
            country=country_val,
            sector=(rec.get("sector") or "")[:100] or None,
            status=(rec.get("status") or "")[:50] or None,
        ).on_conflict_do_nothing(constraint="uq_entities_source")
        await session.execute(stmt)
        counts["entities"] += 1

    # -- TimeSeries --
    for rec in result.time_series:
        ts_val = rec.get("timestamp")
        if ts_val is None:
            continue
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        stmt = pg_insert(TimeSeries).values(
            id=uuid.uuid4(),
            source_name=rec.get("source_name", ""),
            source_id=rec.get("source_id", ""),
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            code=rec.get("code", "unknown"),
            name=rec.get("name"),
            timestamp=ts_val,
            value=rec.get("value", 0),
            unit=rec.get("unit"),
            commodity=rec.get("commodity"),
            country=rec.get("country"),
        ).on_conflict_do_nothing(constraint="uq_time_series_source")
        await session.execute(stmt)
        counts["time_series"] += 1

    # -- Events --
    for rec in result.events:
        ts_val = rec.get("timestamp")
        if ts_val is None:
            continue
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        stmt = pg_insert(Event).values(
            id=uuid.uuid4(),
            source_name=rec.get("source_name", ""),
            source_id=rec.get("source_id", ""),
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            event_type=rec.get("event_type", "unknown"),
            name=rec.get("name"),
            description=rec.get("description"),
            timestamp=ts_val,
            severity=rec.get("severity"),
            economic_impact=rec.get("economic_impact"),
        ).on_conflict_do_nothing()
        await session.execute(stmt)
        counts["events"] += 1

    # -- Flows --
    for rec in result.flows:
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        stmt = pg_insert(Flow).values(
            id=uuid.uuid4(),
            source_name=rec.get("source_name", ""),
            source_id=rec.get("source_id", ""),
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            flow_type=rec.get("flow_type", "unknown"),
            source_entity_id=rec.get("source_entity_id"),
            dest_entity_id=rec.get("dest_entity_id"),
            timestamp=rec.get("timestamp"),
            amount=rec.get("amount"),
            currency=rec.get("currency"),
            unit=rec.get("unit"),
            commodity=rec.get("commodity"),
            purpose=rec.get("purpose"),
        ).on_conflict_do_nothing()
        await session.execute(stmt)
        counts["flows"] += 1

    # -- Assessments --
    for rec in result.assessments:
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        stmt = pg_insert(Assessment).values(
            id=uuid.uuid4(),
            source_name=rec.get("source_name", ""),
            source_id=rec.get("source_id", ""),
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            entity_id=rec.get("entity_id"),
            assessor=rec.get("assessor", "unknown"),
            metric_code=rec.get("metric_code", "unknown"),
            timestamp=rec.get("timestamp"),
            score_numeric=rec.get("score_numeric"),
            score_category=rec.get("score_category"),
            confidence=rec.get("confidence"),
            trend=rec.get("trend"),
        ).on_conflict_do_nothing()
        await session.execute(stmt)
        counts["assessments"] += 1

    # -- Claims --
    for rec in result.claims:
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        stmt = pg_insert(Claim).values(
            id=uuid.uuid4(),
            source_name=rec.get("source_name", ""),
            source_id=rec.get("source_id", ""),
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            claimant_entity_id=rec.get("claimant_entity_id"),
            name=rec.get("name"),
            target_value=rec.get("target_value"),
            target_unit=rec.get("target_unit"),
            deadline=rec.get("deadline"),
            status=rec.get("status"),
            progress_percent=rec.get("progress_percent"),
        ).on_conflict_do_nothing()
        await session.execute(stmt)
        counts["claims"] += 1

    # -- Relationships --
    for rec in result.relationships:
        src_eid = rec.get("source_entity_id")
        dst_eid = rec.get("dest_entity_id")
        if not src_eid or not dst_eid:
            continue
        geom = _geojson_to_wkb(rec.pop("geometry", None))
        stmt = pg_insert(Relationship).values(
            id=uuid.uuid4(),
            source_name=rec.get("source_name", ""),
            source_id=rec.get("source_id", ""),
            quality_score=rec.get("quality_score"),
            geometry=geom,
            payload=rec.get("payload"),
            source_entity_id=src_eid,
            dest_entity_id=dst_eid,
            relationship_type=rec.get("relationship_type", "relates_to"),
            strength=rec.get("strength"),
            status=rec.get("status"),
        ).on_conflict_do_nothing()
        await session.execute(stmt)
        counts["relationships"] += 1

    return counts


# ===================================================================
# ESVD special ingest (load CSV -> observations -> promote)
# ===================================================================

async def _ingest_esvd(session, dry_run: bool) -> dict[str, int]:
    """Load ESVD CSV with global bbox, promote through the ESVD mapper."""
    log.info("ESVD: loading CSV with global bbox...")
    adapter = EsvdAdapter()
    records = await adapter.fetch(
        bbox=(-180.0, -90.0, 180.0, 90.0),
        time_start=datetime(1900, 1, 1, tzinfo=timezone.utc),
        time_end=datetime(2030, 12, 31, tzinfo=timezone.utc),
        limit=50000,
    )
    log.info("ESVD: %d records from CSV", len(records))
    if not records:
        return {"esvd_records": 0}

    # Route through transform (ESVD mapper is registered in mappers.py)
    result, unmapped = transform(records)
    log.info("ESVD transform: entities=%d, assessments=%d, unmapped=%d",
             len(result.entities), len(result.assessments), len(unmapped))

    if dry_run:
        return {"esvd_entities": len(result.entities),
                "esvd_assessments": len(result.assessments)}

    counts = await _persist_results(session, result)
    return {f"esvd_{k}": v for k, v in counts.items()}


# ===================================================================
# Main pipeline
# ===================================================================

async def main(dry_run: bool = False) -> None:
    log.info("=" * 70)
    log.info("PROMOTE OBSERVATIONS%s", " (DRY RUN)" if dry_run else "")
    log.info("Registered mappers: %d", len(MAPPER_REGISTRY))
    log.info("  Sources: %s", ", ".join(sorted(MAPPER_REGISTRY.keys())))
    log.info("=" * 70)

    # --- Phase 1: Read observations from DB, grouped by source_name ---
    async with get_session() as session:
        # Get distinct source_names and counts (raw SQL to avoid STI issues)
        src_rows = (await session.execute(
            text("SELECT source_name, count(*) AS cnt FROM observations GROUP BY source_name")
        )).all()

    source_counts = {row.source_name: row.cnt for row in src_rows}
    total_obs = sum(source_counts.values())
    log.info("Found %d observations across %d sources", total_obs, len(source_counts))

    mapped_sources = []
    unmapped_sources = []
    for sn in sorted(source_counts.keys()):
        if sn in MAPPER_REGISTRY:
            mapped_sources.append(sn)
        else:
            unmapped_sources.append(sn)

    log.info("Mapped sources (%d): %s", len(mapped_sources), ", ".join(mapped_sources))
    log.info("Unmapped sources (%d): %s", len(unmapped_sources), ", ".join(unmapped_sources[:20]))
    if len(unmapped_sources) > 20:
        log.info("  ... and %d more", len(unmapped_sources) - 20)

    # --- Phase 2: Process each source in batches ---
    grand_totals: dict[str, int] = {
        "entities": 0, "time_series": 0, "events": 0,
        "flows": 0, "assessments": 0, "claims": 0, "relationships": 0,
    }
    processed = 0

    for source_name in sorted(source_counts.keys()):
        count = source_counts[source_name]
        has_mapper = source_name in MAPPER_REGISTRY
        mapper_type = "registered" if has_mapper else "generic"

        log.info("Processing %-35s (%5d obs, %s mapper)", source_name, count, mapper_type)

        # Read observations for this source in batches
        offset = 0
        source_totals: dict[str, int] = {k: 0 for k in grand_totals}

        while offset < count:
            async with get_session() as session:
                # Use raw SQL to avoid STI polymorphic identity issues
                sql = text("""
                    SELECT id, obs_type, timestamp, geometry, source_id,
                           source_name, quality_score, payload
                    FROM observations
                    WHERE source_name = :sn
                    ORDER BY id
                    OFFSET :off LIMIT :lim
                """)
                raw_rows = (await session.execute(
                    sql, {"sn": source_name, "off": offset, "lim": BATCH_SIZE}
                )).fetchall()

                if not raw_rows:
                    break

                # Convert raw rows to dicts (same shape as adapter output)
                records = []
                for row in raw_rows:
                    geom = None
                    if row.geometry is not None:
                        try:
                            from shapely import wkb as _wkb
                            shapely_geom = _wkb.loads(bytes(row.geometry))
                            geom = shapely_geom.__geo_interface__
                        except Exception:
                            pass

                    records.append({
                        "obs_type": row.obs_type,
                        "timestamp": row.timestamp,
                        "geometry": geom,
                        "source_id": row.source_id,
                        "source_name": row.source_name,
                        "quality_score": row.quality_score,
                        "payload": row.payload or {},
                    })

                # Transform
                if has_mapper:
                    result, unmapped = transform(records)
                    # Also run generic mapper on any unmapped within this batch
                    if unmapped:
                        generic_result = _generic_mapper(unmapped)
                        result.entities.extend(generic_result.entities)
                else:
                    result = _generic_mapper(records)

                if not dry_run:
                    batch_counts = await _persist_results(session, result)
                    for k, v in batch_counts.items():
                        source_totals[k] += v
                else:
                    source_totals["entities"] += len(result.entities)
                    source_totals["time_series"] += len(result.time_series)
                    source_totals["events"] += len(result.events)
                    source_totals["flows"] += len(result.flows)
                    source_totals["assessments"] += len(result.assessments)
                    source_totals["claims"] += len(result.claims)
                    source_totals["relationships"] += len(result.relationships)

                offset += len(raw_rows)
                processed += len(raw_rows)

        # Log source summary (only non-zero)
        non_zero = {k: v for k, v in source_totals.items() if v > 0}
        if non_zero:
            log.info("  -> %s", non_zero)
        for k in grand_totals:
            grand_totals[k] += source_totals[k]

    # --- Phase 3: ESVD special ingest ---
    log.info("-" * 70)
    log.info("ESVD special ingest (CSV with global bbox)...")
    async with get_session() as session:
        esvd_counts = await _ingest_esvd(session, dry_run)
    log.info("ESVD results: %s", esvd_counts)

    # --- Phase 4: Graph backfill ---
    if not dry_run:
        log.info("-" * 70)
        log.info("Running knowledge graph backfill...")
        try:
            from okeanus.ml.graph.builder import KnowledgeGraphBuilder
            builder = KnowledgeGraphBuilder()
            session = async_session_factory()
            try:
                graph_counts = await builder.backfill_all(session, run_correlations=True)
                await session.commit()
                log.info("Graph backfill: %s", graph_counts)
            except Exception as exc:
                await session.rollback()
                log.error("Graph backfill failed: %s", exc)
            finally:
                await session.close()
        except Exception as exc:
            log.error("Could not import graph builder: %s", exc)

    # --- Summary ---
    log.info("=" * 70)
    log.info("PROMOTION COMPLETE%s", " (DRY RUN)" if dry_run else "")
    log.info("Observations processed: %d / %d", processed, total_obs)
    log.info("Results:")
    for k, v in grand_totals.items():
        log.info("  %-15s %d", k, v)
    log.info("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote observations to structured tables")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
