"""Vessel risk scoring API endpoints.

Provides composite risk assessment combining flag state, AIS gaps,
behavioral analysis, encounter patterns, geofence violations, and
identity anomalies into a single actionable score.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from okeanus.ml.risk.scoring import (
    DEFAULT_WEIGHTS,
    get_factor_descriptions,
    score_fleet,
    score_vessel,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml/risk", tags=["ml", "risk"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class BatchScoreRequest(BaseModel):
    mmsis: list[int] = Field(..., min_length=1, max_length=100)
    weights: dict[str, float] | None = None
    include_factors: list[str] | None = None


class WeightOverride(BaseModel):
    weights: dict[str, float] = Field(
        ...,
        description="Factor weights — keys must be valid factor names, values must sum to ~1.0",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/factors")
async def list_risk_factors() -> dict[str, Any]:
    """List all available risk factors with descriptions and default weights.

    Returns metadata about each factor including what data it uses,
    how it scores risk, and its default weight in the composite score.
    """
    factors = get_factor_descriptions()
    return {
        "factor_count": len(factors),
        "default_weights": DEFAULT_WEIGHTS,
        "factors": factors,
    }


@router.get("/{mmsi}")
async def get_vessel_risk(
    mmsi: int,
    include_factors: Annotated[
        str | None,
        Query(
            description="Comma-separated factor names to include (default: all). "
            "Options: flag_state, ais_gap, behavioral, encounter, geofence, identity"
        ),
    ] = None,
    flag_override: Annotated[
        str | None,
        Query(
            description="Override flag state detection with ISO-2 country code",
            max_length=2,
        ),
    ] = None,
) -> dict[str, Any]:
    """Compute composite risk score for a single vessel.

    Returns a 0-100 risk score with classification (LOW/MEDIUM/HIGH/CRITICAL),
    individual factor scores, evidence items, and a human-readable summary.

    The score combines six risk dimensions:
    - **flag_state** (15%): Flag state IUU compliance index
    - **ais_gap** (20%): AIS transmission gap analysis
    - **behavioral** (20%): Movement pattern anomalies
    - **encounter** (15%): Suspicious vessel meetings
    - **geofence** (15%): Zone violation history
    - **identity** (15%): Vessel identity anomalies
    """
    factors = None
    if include_factors:
        factors = [f.strip() for f in include_factors.split(",")]

    result = await score_vessel(
        mmsi=mmsi,
        include_factors=factors,
        flag_override=flag_override,
    )
    return result.to_dict()


@router.post("/batch")
async def batch_risk_score(request: BatchScoreRequest) -> dict[str, Any]:
    """Score multiple vessels in a single request.

    Evaluates up to 100 vessels concurrently and returns individual
    scores plus fleet-level statistics.
    """
    scores = await score_fleet(
        mmsis=request.mmsis,
        weights=request.weights,
        include_factors=request.include_factors,
    )

    # Fleet statistics
    all_scores = [s.composite_score for s in scores]
    by_level: dict[str, int] = {}
    for s in scores:
        by_level[s.risk_level.value] = by_level.get(s.risk_level.value, 0) + 1

    return {
        "vessel_count": len(scores),
        "fleet_stats": {
            "mean_score": round(sum(all_scores) / len(all_scores), 2) if all_scores else 0,
            "max_score": round(max(all_scores), 2) if all_scores else 0,
            "min_score": round(min(all_scores), 2) if all_scores else 0,
            "by_risk_level": by_level,
        },
        "vessels": [s.to_dict() for s in scores],
    }


@router.get("/fleet/summary")
async def fleet_risk_summary(
    limit: Annotated[
        int, Query(ge=1, le=100, description="Max vessels to return")
    ] = 20,
    min_score: Annotated[
        float, Query(ge=0, le=100, description="Minimum risk score filter")
    ] = 0,
) -> dict[str, Any]:
    """Get a fleet-wide risk summary.

    Returns the highest-risk vessels across all tracked MMSIs.
    Queries the most recently active vessels and scores them.
    """
    # Fetch recently active vessels from DB
    mmsis = await _get_active_mmsis(limit=limit * 2)  # over-fetch for filtering

    if not mmsis:
        return {
            "vessel_count": 0,
            "message": "No active vessels found",
            "vessels": [],
        }

    scores = await score_fleet(mmsis=mmsis)

    # Filter and sort
    filtered = [s for s in scores if s.composite_score >= min_score]
    filtered.sort(key=lambda s: s.composite_score, reverse=True)
    top = filtered[:limit]

    by_level: dict[str, int] = {}
    for s in filtered:
        by_level[s.risk_level.value] = by_level.get(s.risk_level.value, 0) + 1

    return {
        "total_scored": len(scores),
        "above_threshold": len(filtered),
        "by_risk_level": by_level,
        "vessels": [
            {
                "mmsi": s.mmsi,
                "composite_score": round(s.composite_score, 2),
                "risk_level": s.risk_level.value,
                "summary": s._summary(),
            }
            for s in top
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_active_mmsis(limit: int = 50) -> list[int]:
    """Fetch recently active vessel MMSIs from the database."""
    try:
        from okeanus.db.postgres import async_session_factory
        from okeanus.schema.vessel import VesselObservation

        from sqlalchemy import func, select

        async with async_session_factory() as session:
            stmt = (
                select(VesselObservation.mmsi)
                .where(VesselObservation.mmsi.isnot(None))
                .group_by(VesselObservation.mmsi)
                .order_by(func.max(VesselObservation.timestamp).desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]
    except Exception as exc:
        logger.warning("Could not fetch active MMSIs: %s", exc)
        return []
