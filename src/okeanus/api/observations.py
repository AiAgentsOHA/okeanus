"""Observation query endpoints returning GeoJSON."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query
from geoalchemy2.functions import ST_MakeEnvelope
from geojson_pydantic import FeatureCollection
from sqlalchemy import select

from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation, ObservationBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/observations", tags=["observations"])

VALID_OBS_TYPES = {"physical", "vessel", "acoustic", "biological", "satellite", "economic"}


def _row_to_feature(row: Observation) -> dict[str, Any]:
    obs = ObservationBase.model_validate(row)
    return obs.to_feature().model_dump()


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
    """Query observations with spatial, temporal, and source filters."""
    if obs_type and obs_type not in VALID_OBS_TYPES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Invalid obs_type '{obs_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_OBS_TYPES))}",
        )

    stmt = select(Observation)

    if bbox:
        w, s, e, n = [float(x) for x in bbox.split(",")]
        stmt = stmt.where(
            Observation.geometry.ST_Intersects(ST_MakeEnvelope(w, s, e, n, 4326))
        )
    if time_start:
        stmt = stmt.where(Observation.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(Observation.timestamp <= time_end)
    if source_name:
        stmt = stmt.where(Observation.source_name == source_name)
    if obs_type:
        stmt = stmt.where(Observation.obs_type == obs_type)

    stmt = stmt.order_by(Observation.timestamp.desc()).offset(offset).limit(limit)

    async with async_session_factory() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    features = [_row_to_feature(r) for r in rows]
    return FeatureCollection(type="FeatureCollection", features=features)
