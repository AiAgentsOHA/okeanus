"""Batch ingest: fetch from no-auth adapters → transform → persist to economy tables.

Usage:
    .venv/bin/python3 scripts/batch_ingest.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone

from geoalchemy2.shape import from_shape
from shapely.geometry import shape
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Ensure mappers are registered
import okeanus.transform.mappers  # noqa: F401
from okeanus.adapters import ADAPTER_REGISTRY
from okeanus.db.postgres import get_session
from okeanus.schema.economy import Entity, TimeSeries, Event
from okeanus.transform.pipeline import (
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
log = logging.getLogger("batch_ingest")


# ===================================================================
# Mappers for no-auth adapters (observation → economy format)
# ===================================================================


def _base(rec: dict) -> dict:
    return {
        "source_name": rec.get("source_name"),
        "source_id": rec.get("source_id", ""),
        "quality_score": rec.get("quality_score"),
        "geometry": rec.get("geometry"),
    }


@register_mapper("OBIS")
def _obis(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        name = p.get("scientific_name") or p.get("species") or "Unknown"
        b = _base(rec)
        b.update(
            id=entity_uuid("OBIS", rec["source_id"]),
            entity_type="species_observation",
            name=name,
            sector="biodiversity",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("GBIF")
def _gbif(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        name = p.get("scientific_name") or p.get("species") or "Unknown"
        b = _base(rec)
        b.update(
            id=entity_uuid("GBIF", rec["source_id"]),
            entity_type="species_observation",
            name=name,
            country=p.get("country"),
            sector="biodiversity",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("USGS Earthquakes")
def _usgs_quakes(records: list[dict]) -> TransformResult:
    evts = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        mag = p.get("magnitude")
        severity = None
        if mag is not None:
            severity = "high" if mag >= 5.0 else ("medium" if mag >= 3.0 else "low")
        b.update(
            event_type="earthquake",
            name=p.get("title", f"M{mag} Earthquake"),
            description=p.get("place", ""),
            timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
            severity=severity,
            payload=p,
        )
        evts.append(b)
    return TransformResult(events=evts)


@register_mapper("NOAA CO-OPS")
def _noaa_coops(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        val = p.get("value") or p.get("water_level")
        if val is None:
            continue
        b = _base(rec)
        b.update(
            code=f"coops-{p.get('station_id', 'unknown')}-water_level",
            name=p.get("station_name", "NOAA CO-OPS Station"),
            timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
            value=float(val),
            unit="meters",
            payload=p,
        )
        ts.append(b)
    return TransformResult(time_series=ts)


@register_mapper("NDBC")
def _ndbc(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        val = p.get("wave_height") or p.get("wind_speed")
        if val is None:
            continue
        metric = "wave_height" if p.get("wave_height") else "wind_speed"
        unit = "meters" if metric == "wave_height" else "m/s"
        b = _base(rec)
        b.update(
            code=f"ndbc-{p.get('station_id', 'unknown')}-{metric}",
            name=f"NDBC {metric}",
            timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
            value=float(val),
            unit=unit,
            payload=p,
        )
        ts.append(b)
    return TransformResult(time_series=ts)


@register_mapper("PSMSL")
def _psmsl(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        val = p.get("rlr") or p.get("sea_level") or p.get("metric")
        if val is None:
            continue
        b = _base(rec)
        b.update(
            code=f"psmsl-{p.get('station_id', 'unknown')}-sea_level",
            name=p.get("station_name", "PSMSL Station"),
            timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
            value=float(val),
            unit="mm",
            payload=p,
        )
        ts.append(b)
    return TransformResult(time_series=ts)


@register_mapper("InterRidge")
def _interridge(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        b.update(
            id=entity_uuid("InterRidge", rec["source_id"]),
            entity_type="hydrothermal_vent",
            name=p.get("name") or p.get("site_name") or "Unknown Vent",
            sector="geology",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("NOAA Wrecks & Obstructions")
def _noaa_wrecks(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        b.update(
            id=entity_uuid("NOAA Wrecks", rec["source_id"]),
            entity_type="shipwreck",
            name=p.get("vesselname") or p.get("name") or "Unknown Wreck",
            sector="maritime_heritage",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("Marine Regions")
def _marine_regions(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        b.update(
            id=entity_uuid("Marine Regions", rec["source_id"]),
            entity_type="marine_region",
            name=p.get("name") or p.get("preferredGazetteerName") or "Unknown Region",
            identifier=str(p.get("mrgid") or p.get("MRGID") or ""),
            sector="geography",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("WoRMS")
def _worms(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        b.update(
            id=entity_uuid("WoRMS", rec["source_id"]),
            entity_type="taxon",
            name=p.get("scientificname") or p.get("scientific_name") or "Unknown Taxon",
            identifier=str(p.get("AphiaID", "")),
            sector="taxonomy",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("OpenSanctions")
def _opensanctions(records: list[dict]) -> TransformResult:
    ents = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        b.update(
            id=entity_uuid("OpenSanctions", rec["source_id"]),
            entity_type="sanctioned_entity",
            name=p.get("name") or p.get("caption") or "Unknown Entity",
            country=p.get("country"),
            sector="compliance",
            status="sanctioned",
            payload=p,
        )
        ents.append(b)
    return TransformResult(entities=ents)


@register_mapper("Climate Indices")
def _climate_indices(records: list[dict]) -> TransformResult:
    ts = []
    for rec in records:
        p = rec.get("payload", {})
        val = p.get("value")
        if val is None:
            continue
        b = _base(rec)
        b.update(
            code=p.get("index_name", "climate_index"),
            name=p.get("index_name", "Climate Index"),
            timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
            value=float(val),
            unit="index",
            payload=p,
        )
        ts.append(b)
    return TransformResult(time_series=ts)


@register_mapper("NOAA Storm Events")
def _noaa_storm_events(records: list[dict]) -> TransformResult:
    evts = []
    for rec in records:
        p = rec.get("payload", {})
        b = _base(rec)
        b.update(
            event_type=p.get("event_type", "storm"),
            name=p.get("event_type", "Storm Event"),
            description=p.get("event_narrative", ""),
            timestamp=rec.get("timestamp", datetime.now(timezone.utc)),
            severity=p.get("magnitude_type", "medium"),
            economic_impact=p.get("damage_property"),
            payload=p,
        )
        evts.append(b)
    return TransformResult(events=evts)


# ===================================================================
# Adapter config: (registry_key, bbox, extra_params)
# ===================================================================

# South African coast + East Africa — good data density
BBOX_SA = (15.0, -35.0, 40.0, -22.0)
# Global for some datasets
BBOX_GLOBAL = (-180.0, -90.0, 180.0, 90.0)
# Recent time range
T_START = datetime(2024, 1, 1, tzinfo=timezone.utc)
T_END = datetime(2025, 6, 1, tzinfo=timezone.utc)

ADAPTERS_TO_RUN: list[dict] = [
    {"key": "obis", "bbox": BBOX_SA, "params": {"limit": 300}},
    {"key": "gbif", "bbox": BBOX_SA, "params": {"limit": 300}},
    {"key": "usgs_quakes", "bbox": BBOX_GLOBAL, "params": {"limit": 200, "min_magnitude": 4.0}},
    {"key": "noaa_coops", "bbox": (-80.0, 25.0, -65.0, 45.0), "params": {"limit": 200}},
    {"key": "ndbc", "bbox": (-180.0, -90.0, 180.0, 90.0), "params": {"limit": 200}},
    {"key": "psmsl", "bbox": BBOX_GLOBAL, "params": {"limit": 200}},
    {"key": "interridge", "bbox": BBOX_GLOBAL, "params": {"limit": 200}},
    {"key": "noaa_wrecks", "bbox": (-80.0, 25.0, -65.0, 45.0), "params": {"limit": 200}},
    {"key": "marine_regions", "bbox": BBOX_SA, "params": {"limit": 200}},
    {"key": "worms", "bbox": BBOX_GLOBAL, "params": {"limit": 200}},
    {"key": "climate_indices", "bbox": BBOX_GLOBAL, "params": {"limit": 300}},
    {"key": "noaa_storm_events", "bbox": (-100.0, 20.0, -60.0, 50.0), "params": {"limit": 200}},
]


def _geojson_to_wkb(geom: dict | None):
    """Convert GeoJSON dict to WKBElement for geoalchemy2, or return None."""
    if geom is None:
        return None
    try:
        shapely_geom = shape(geom)
        return from_shape(shapely_geom, srid=4326)
    except Exception:
        return None


async def _persist_results(result: TransformResult) -> dict[str, int]:
    """Persist transformed records to economy tables using upsert."""
    counts = {"entities": 0, "time_series": 0, "events": 0}

    async with get_session() as session:
        # -- Entities --
        for rec in result.entities:
            ent_id = rec.pop("id", None) or uuid.uuid4()
            geom = _geojson_to_wkb(rec.pop("geometry", None))
            stmt = pg_insert(Entity).values(
                id=ent_id,
                source_name=rec["source_name"],
                source_id=rec["source_id"],
                quality_score=rec.get("quality_score"),
                geometry=geom,
                payload=rec.get("payload"),
                entity_type=rec["entity_type"],
                name=rec["name"],
                identifier=rec.get("identifier"),
                country=rec.get("country"),
                sector=rec.get("sector"),
                status=rec.get("status"),
            ).on_conflict_do_nothing(constraint="uq_entities_source")
            await session.execute(stmt)
            counts["entities"] += 1

        # -- TimeSeries --
        for rec in result.time_series:
            ts_id = uuid.uuid4()
            geom = _geojson_to_wkb(rec.pop("geometry", None))
            ts_val = rec.get("timestamp")
            if ts_val is None:
                continue
            stmt = pg_insert(TimeSeries).values(
                id=ts_id,
                source_name=rec["source_name"],
                source_id=rec["source_id"],
                quality_score=rec.get("quality_score"),
                geometry=geom,
                payload=rec.get("payload"),
                code=rec["code"],
                name=rec.get("name"),
                timestamp=ts_val,
                value=rec["value"],
                unit=rec.get("unit"),
                commodity=rec.get("commodity"),
                country=rec.get("country"),
            ).on_conflict_do_nothing(constraint="uq_time_series_source")
            await session.execute(stmt)
            counts["time_series"] += 1

        # -- Events --
        for rec in result.events:
            evt_id = uuid.uuid4()
            geom = _geojson_to_wkb(rec.pop("geometry", None))
            ts_val = rec.get("timestamp")
            if ts_val is None:
                continue
            stmt = pg_insert(Event).values(
                id=evt_id,
                source_name=rec["source_name"],
                source_id=rec["source_id"],
                quality_score=rec.get("quality_score"),
                geometry=geom,
                payload=rec.get("payload"),
                event_type=rec["event_type"],
                name=rec.get("name"),
                description=rec.get("description"),
                timestamp=ts_val,
                severity=rec.get("severity"),
                economic_impact=rec.get("economic_impact"),
            ).on_conflict_do_nothing()
            await session.execute(stmt)
            counts["events"] += 1

    return counts


async def main() -> None:
    log.info("=" * 60)
    log.info("BATCH INGEST — %d adapters", len(ADAPTERS_TO_RUN))
    log.info("=" * 60)

    all_records: list[dict] = []
    adapter_results: dict[str, int] = {}

    for cfg in ADAPTERS_TO_RUN:
        key = cfg["key"]
        cls = ADAPTER_REGISTRY.get(key)
        if cls is None:
            log.warning("SKIP %s — not in registry", key)
            continue

        adapter = cls()
        bbox = cfg["bbox"]
        params = cfg.get("params", {})

        log.info("FETCH %-20s bbox=%s limit=%s", key, bbox, params.get("limit", "?"))
        try:
            records = await adapter.fetch(bbox, T_START, T_END, **params)
            log.info("  → %d records from %s", len(records), key)
            all_records.extend(records)
            adapter_results[key] = len(records)
        except Exception as exc:
            log.error("  FAIL %s: %s", key, exc)
            adapter_results[key] = -1

    log.info("-" * 60)
    log.info("Total raw records: %d", len(all_records))

    # Transform
    result, unmapped = transform(all_records)
    log.info("Transform results:")
    log.info("  entities:    %d", len(result.entities))
    log.info("  time_series: %d", len(result.time_series))
    log.info("  events:      %d", len(result.events))
    log.info("  flows:       %d", len(result.flows))
    log.info("  assessments: %d", len(result.assessments))
    log.info("  claims:      %d", len(result.claims))
    log.info("  unmapped:    %d", len(unmapped))

    if not any([result.entities, result.time_series, result.events]):
        log.warning("No data to persist! Check adapter responses.")
        return

    # Persist
    log.info("Persisting to database...")
    counts = await _persist_results(result)
    log.info("Persisted: %s", counts)

    # Summary
    log.info("=" * 60)
    log.info("DONE — Adapter results:")
    for k, v in adapter_results.items():
        status = f"{v} records" if v >= 0 else "FAILED"
        log.info("  %-20s %s", k, status)
    log.info("Economy tables filled: %s", counts)


if __name__ == "__main__":
    asyncio.run(main())
