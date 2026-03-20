"""Geospatial analytics API routes."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.db.postgres import get_session
from okeanus.ml.geospatial import GeospatialEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["geospatial"])

_engine = GeospatialEngine()


async def _get_session():
    async with get_session() as session:
        yield session


@router.get("/spatial-clusters")
async def spatial_clusters(
    session: AsyncSession = Depends(_get_session),
    eps_km: Annotated[float, Query(ge=1, le=500, description="DBSCAN epsilon in km")] = 50.0,
    min_samples: Annotated[int, Query(ge=2, le=100, description="Minimum cluster size")] = 5,
    obs_type: Annotated[str | None, Query(description="Observation type filter")] = None,
) -> list[dict[str, Any]]:
    """DBSCAN spatial clustering on observations."""
    return await _engine.spatial_clusters(
        session, eps_km=eps_km, min_samples=min_samples, obs_type=obs_type,
    )


@router.get("/hotspots")
async def hotspots(
    session: AsyncSession = Depends(_get_session),
    resolution_deg: Annotated[float, Query(ge=0.1, le=10.0, description="Grid resolution in degrees")] = 1.0,
    obs_type: Annotated[str | None, Query(description="Observation type filter")] = None,
) -> list[dict[str, Any]]:
    """Getis-Ord Gi* hotspot analysis."""
    return await _engine.hotspot_analysis(
        session, resolution_deg=resolution_deg, obs_type=obs_type,
    )


@router.get("/trajectories")
async def trajectories(
    session: AsyncSession = Depends(_get_session),
    min_points: Annotated[int, Query(ge=3, le=1000, description="Minimum points per trajectory")] = 10,
) -> list[dict[str, Any]]:
    """Vessel trajectory analysis from AIS observations."""
    return await _engine.trajectory_analysis(session, min_points=min_points)


@router.get("/encounters")
async def encounters(
    session: AsyncSession = Depends(_get_session),
    proximity_km: Annotated[float, Query(ge=0.1, le=50.0, description="Proximity threshold in km")] = 1.0,
    duration_hours: Annotated[float, Query(ge=0.1, le=48.0, description="Minimum duration in hours")] = 1.0,
) -> list[dict[str, Any]]:
    """Detect vessel encounters via PostGIS spatial joins."""
    return await _engine.encounter_detection(
        session, proximity_km=proximity_km, duration_hours=duration_hours,
    )


@router.get("/autocorrelation")
async def autocorrelation(
    session: AsyncSession = Depends(_get_session),
    value_field: Annotated[str, Query(description="Numeric field to test")] = "quality_score",
    resolution_deg: Annotated[float, Query(ge=0.5, le=10.0, description="Grid resolution in degrees")] = 2.0,
) -> dict[str, Any]:
    """Global Moran's I spatial autocorrelation test."""
    return await _engine.spatial_autocorrelation(
        session, value_field=value_field, resolution_deg=resolution_deg,
    )


@router.get("/density")
async def density(
    session: AsyncSession = Depends(_get_session),
    resolution_deg: Annotated[float, Query(ge=0.1, le=10.0, description="Grid resolution in degrees")] = 0.5,
    obs_type: Annotated[str | None, Query(description="Observation type filter")] = None,
) -> list[dict[str, Any]]:
    """Observation density surface for heatmap visualization."""
    return await _engine.density_surface(
        session, resolution_deg=resolution_deg, obs_type=obs_type,
    )
