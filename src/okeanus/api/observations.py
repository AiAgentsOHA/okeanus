"""Observation query endpoints returning GeoJSON."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Query
from geojson_pydantic import Feature, FeatureCollection, Point

router = APIRouter(prefix="/observations", tags=["observations"])

# Allowed obs_type values
VALID_OBS_TYPES = {"physical", "vessel", "acoustic", "biological", "satellite"}


def _mock_observations(
    bbox: tuple[float, float, float, float] | None,
    time_start: datetime | None,
    time_end: datetime | None,
    source_name: str | None,
    obs_type: str | None,
    limit: int,
    offset: int,
) -> FeatureCollection:
    """Generate mock observation data for MVP when no database is connected."""
    import random

    random.seed(42)
    west, south, east, north = bbox or (-180.0, -90.0, 180.0, 90.0)
    features: list[Feature] = []
    for i in range(offset, offset + limit):
        lon = west + random.random() * (east - west)
        lat = south + random.random() * (north - south)
        otype = obs_type or random.choice(list(VALID_OBS_TYPES))
        features.append(
            Feature(
                type="Feature",
                id=str(uuid.uuid4()),
                geometry=Point(type="Point", coordinates=[round(lon, 6), round(lat, 6)]),
                properties={
                    "obs_type": otype,
                    "timestamp": (
                        time_start or datetime(2025, 1, 1, tzinfo=timezone.utc)
                    ).isoformat(),
                    "source_name": source_name or "mock",
                    "source_id": f"mock-{i}",
                    "quality_score": round(random.random(), 2),
                },
            )
        )
    return FeatureCollection(type="FeatureCollection", features=features)


@router.get("", response_model=FeatureCollection)
async def list_observations(
    bbox: Annotated[
        str | None,
        Query(
            description="Bounding box filter: west,south,east,north (EPSG:4326)",
            pattern=r"^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$",
        ),
    ] = None,
    time_start: Annotated[
        datetime | None,
        Query(description="Start of time range (ISO 8601)"),
    ] = None,
    time_end: Annotated[
        datetime | None,
        Query(description="End of time range (ISO 8601)"),
    ] = None,
    source_name: Annotated[
        str | None,
        Query(description="Filter by data source name"),
    ] = None,
    obs_type: Annotated[
        str | None,
        Query(description="Observation type: physical, vessel, acoustic, biological, satellite"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FeatureCollection:
    """Query observations with spatial, temporal, and source filters.

    Returns a GeoJSON FeatureCollection. For MVP, returns mock data when
    no database is connected.
    """
    parsed_bbox = None
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        parsed_bbox = (parts[0], parts[1], parts[2], parts[3])

    if obs_type and obs_type not in VALID_OBS_TYPES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Invalid obs_type '{obs_type}'. Must be one of: {', '.join(sorted(VALID_OBS_TYPES))}",
        )

    # MVP: return mock data (replace with real DB queries when connected)
    return _mock_observations(
        bbox=parsed_bbox,
        time_start=time_start,
        time_end=time_end,
        source_name=source_name,
        obs_type=obs_type,
        limit=limit,
        offset=offset,
    )
