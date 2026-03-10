"""Data ingestion endpoints -- fetch from adapters and store in PostGIS."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from okeanus.config import settings
from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


def _dict_to_observation(record: dict[str, Any]) -> Observation:
    """Convert an adapter output dict into an ORM Observation."""
    geom = record.pop("geometry")
    shapely_geom = shape(geom)
    wkb_geom = from_shape(shapely_geom, srid=4326)

    obs = Observation(
        obs_type=record.pop("obs_type", "physical"),
        timestamp=record.pop("timestamp"),
        geometry=wkb_geom,
        source_id=record.pop("source_id"),
        source_name=record.pop("source_name"),
        quality_score=record.pop("quality_score", None),
        aphia_id=record.pop("aphia_id", None),
        mrgid=record.pop("mrgid", None),
        mmsi=record.pop("mmsi", None),
        payload=record if record else None,
    )
    return obs


@router.post("/fetch/{source}")
async def ingest_from_source(
    source: str,
    bbox: Annotated[
        str,
        Query(description="Bounding box: west,south,east,north"),
    ],
    time_start: Annotated[datetime, Query(description="Start time (ISO 8601)")],
    time_end: Annotated[datetime, Query(description="End time (ISO 8601)")],
    variable: Annotated[str | None, Query(description="Variable (e.g. sst, currents)")] = None,
) -> dict[str, Any]:
    """Fetch data from an adapter and store in PostGIS.

    Returns the count of observations ingested.
    """
    w, s, e, n = [float(x) for x in bbox.split(",")]
    bbox_tuple = (w, s, e, n)

    if source == "cmems":
        from okeanus.adapters.cmems import CmemsAdapter

        adapter = CmemsAdapter(
            username=settings.cmems_username,
            password=settings.cmems_password,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source '{source}'. Available: cmems",
        )

    params: dict[str, Any] = {}
    if variable:
        params["variable"] = variable

    records = await adapter.fetch(bbox_tuple, time_start, time_end, **params)

    if not records:
        return {"source": source, "ingested": 0, "message": "No records returned"}

    observations = [_dict_to_observation(r) for r in records]

    async with async_session_factory() as session:
        session.add_all(observations)
        await session.commit()

    logger.info("Ingested %d records from %s", len(observations), source)
    return {"source": source, "ingested": len(observations)}
