"""Vessel position endpoints returning GeoJSON."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from geoalchemy2.functions import ST_MakeEnvelope
from geojson_pydantic import Feature, FeatureCollection
from sqlalchemy import select

from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation, ObservationBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vessels", tags=["vessels"])


@router.get("", response_model=FeatureCollection)
async def list_vessels(
    mmsi: Annotated[int | None, Query(description="Filter by MMSI number")] = None,
    bbox: Annotated[
        str | None,
        Query(
            description="Bounding box: west,south,east,north",
            pattern=r"^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> FeatureCollection:
    """Query vessel positions by MMSI and bounding box."""
    stmt = select(Observation).where(Observation.obs_type == "vessel")

    if mmsi:
        stmt = stmt.where(Observation.mmsi == mmsi)
    if bbox:
        w, s, e, n = [float(x) for x in bbox.split(",")]
        stmt = stmt.where(
            Observation.geometry.ST_Intersects(ST_MakeEnvelope(w, s, e, n, 4326))
        )

    stmt = stmt.order_by(Observation.timestamp.desc()).limit(limit)

    async with async_session_factory() as session:
        result = await session.execute(stmt)
        rows = result.scalars().all()

    features = [ObservationBase.model_validate(r).to_feature().model_dump() for r in rows]
    return FeatureCollection(type="FeatureCollection", features=features)


@router.get("/{mmsi}", response_model=Feature)
async def get_vessel(mmsi: int) -> Feature:
    """Get the latest position for a specific vessel by MMSI."""
    stmt = (
        select(Observation)
        .where(Observation.obs_type == "vessel", Observation.mmsi == mmsi)
        .order_by(Observation.timestamp.desc())
        .limit(1)
    )

    async with async_session_factory() as session:
        result = await session.execute(stmt)
        row = result.scalars().first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Vessel with MMSI {mmsi} not found")

    return ObservationBase.model_validate(row).to_feature()
