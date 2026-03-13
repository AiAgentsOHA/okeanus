"""Core transform framework: registry, dispatch, geometry sanitization, deterministic UUIDs."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TransformResult:
    """Structured output from mapper functions -- one list per target table."""

    time_series: list[dict] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    flows: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    assessments: list[dict] = field(default_factory=list)
    claims: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)


SourceMapper = Callable[[list[dict]], TransformResult]
MAPPER_REGISTRY: dict[str, SourceMapper] = {}


def register_mapper(*source_names: str):
    """Decorator. Registers mapper for one or more source_name strings."""

    def decorator(fn: SourceMapper) -> SourceMapper:
        for name in source_names:
            MAPPER_REGISTRY[name] = fn
        return fn

    return decorator


def sanitize_geometry(geom: dict | None) -> dict | None:
    """Returns None if geometry is null island [0,0], otherwise passes through."""
    if geom is None:
        return None
    coords = geom.get("coordinates")
    if coords and isinstance(coords, (list, tuple)):
        if len(coords) >= 2 and coords[0] == 0 and coords[1] == 0:
            return None
    return geom


def entity_uuid(source_name: str, source_id: str) -> uuid.UUID:
    """Deterministic UUID for entity dedup. Same source+id always -> same UUID."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"okeanus:{source_name}:{source_id}")


def transform(records: list[dict]) -> tuple[TransformResult, list[dict]]:
    """Route records through mappers. Returns (result, unmapped_records)."""
    grouped: dict[str, list[dict]] = {}
    unmapped: list[dict] = []

    for rec in records:
        sn = rec.get("source_name", "")
        if sn in MAPPER_REGISTRY:
            grouped.setdefault(sn, []).append(rec)
        else:
            unmapped.append(rec)

    merged = TransformResult()
    for sn, recs in grouped.items():
        partial = MAPPER_REGISTRY[sn](recs)
        merged.time_series.extend(partial.time_series)
        merged.entities.extend(partial.entities)
        merged.flows.extend(partial.flows)
        merged.events.extend(partial.events)
        merged.assessments.extend(partial.assessments)
        merged.claims.extend(partial.claims)
        merged.relationships.extend(partial.relationships)

    return merged, unmapped
