"""Vessel behavioral analytics API endpoints.

Provides trajectory classification, encounter detection, and voyage
reconstruction from AIS position data.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query

from okeanus.ml.behavioral.encounters import (
    detect_encounters_for_vessel,
    detect_encounters_in_area,
)
from okeanus.ml.behavioral.trajectory import (
    BehaviorType,
    classify_vessel_track,
)
from okeanus.ml.behavioral.voyages import reconstruct_vessel_voyages

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml/behavioral", tags=["ml", "behavioral"])


# ---------------------------------------------------------------------------
# Trajectory classification
# ---------------------------------------------------------------------------


@router.get("/trajectory/{mmsi}")
async def classify_trajectory(
    mmsi: int,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    window_minutes: Annotated[int, Query(ge=5, le=240, description="Classification window")] = 30,
    step_minutes: Annotated[int, Query(ge=1, le=120, description="Sliding window step")] = 15,
) -> dict[str, Any]:
    """Classify vessel trajectory into behaviour segments.

    Returns a sequence of time-stamped behaviour classifications:
    anchored, loitering, fishing, transiting, drifting, maneuvering.
    """
    segments = await classify_vessel_track(
        mmsi=mmsi,
        time_start=time_start,
        time_end=time_end,
        window_minutes=window_minutes,
        step_minutes=step_minutes,
    )

    # Summary statistics
    behavior_summary: dict[str, float] = {}
    total_minutes = sum(s.duration_minutes for s in segments)
    for seg in segments:
        behavior_summary[seg.behavior.value] = (
            behavior_summary.get(seg.behavior.value, 0) + seg.duration_minutes
        )

    return {
        "mmsi": str(mmsi),
        "segment_count": len(segments),
        "total_duration_minutes": round(total_minutes, 1),
        "behavior_summary": {
            k: {
                "minutes": round(v, 1),
                "percentage": round(v / total_minutes * 100, 1) if total_minutes > 0 else 0,
            }
            for k, v in behavior_summary.items()
        },
        "segments": [s.to_dict() for s in segments],
    }


@router.get("/trajectory/{mmsi}/current")
async def current_behavior(mmsi: int) -> dict[str, Any]:
    """Get the current (most recent) behaviour classification for a vessel.

    Uses the last 30 minutes of AIS data to classify current activity.
    """
    from datetime import timezone

    now = datetime.now(timezone.utc)
    segments = await classify_vessel_track(
        mmsi=mmsi,
        time_start=now.replace(minute=now.minute - 30 if now.minute >= 30 else 0),
        time_end=now,
        window_minutes=30,
        step_minutes=30,
    )

    if not segments:
        return {
            "mmsi": str(mmsi),
            "current_behavior": "unknown",
            "confidence": 0.0,
            "message": "No recent AIS data available",
        }

    latest = segments[-1]
    return {
        "mmsi": str(mmsi),
        "current_behavior": latest.behavior.value,
        "confidence": round(latest.confidence, 3),
        "since": latest.start_time.isoformat() if latest.start_time else None,
        "kinematics": {
            "mean_sog_kn": round(latest.mean_sog, 2),
            "cog_variance": round(latest.cog_variance, 4),
            "heading_rate_deg_min": round(latest.heading_rate, 2),
        },
    }


# ---------------------------------------------------------------------------
# Encounter detection
# ---------------------------------------------------------------------------


@router.get("/encounters")
async def find_encounters_in_area(
    bbox: Annotated[
        str,
        Query(
            description="Bounding box: west,south,east,north",
            pattern=r"^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$",
        ),
    ],
    time_start: Annotated[datetime, Query(description="Start time (ISO 8601)")],
    time_end: Annotated[datetime, Query(description="End time (ISO 8601)")],
    distance_threshold_nm: Annotated[
        float, Query(ge=0.05, le=5.0, description="Max distance for encounter (nm)")
    ] = 0.5,
    min_duration_minutes: Annotated[
        float, Query(ge=1, le=1440, description="Min encounter duration (minutes)")
    ] = 10,
) -> dict[str, Any]:
    """Detect vessel encounters in a geographic area and time window.

    Finds pairs of vessels that came within distance_threshold_nm for at
    least min_duration_minutes.  Classifies encounters as rendezvous,
    parallel_transit, crossing, or loitering_pair.
    """
    w, s, e, n = [float(x) for x in bbox.split(",")]
    encounters = await detect_encounters_in_area(
        bbox=(w, s, e, n),
        time_start=time_start,
        time_end=time_end,
        distance_threshold_nm=distance_threshold_nm,
        min_duration_minutes=min_duration_minutes,
    )

    # Summary
    by_type: dict[str, int] = {}
    by_risk: dict[str, int] = {}
    for enc in encounters:
        by_type[enc.encounter_type.value] = by_type.get(enc.encounter_type.value, 0) + 1
        by_risk[enc.risk_level.value] = by_risk.get(enc.risk_level.value, 0) + 1

    return {
        "total_encounters": len(encounters),
        "by_type": by_type,
        "by_risk": by_risk,
        "encounters": [e.to_dict() for e in encounters],
    }


@router.get("/encounters/{mmsi}")
async def find_vessel_encounters(
    mmsi: int,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    distance_threshold_nm: Annotated[
        float, Query(ge=0.05, le=5.0, description="Max distance for encounter (nm)")
    ] = 0.5,
    min_duration_minutes: Annotated[
        float, Query(ge=1, le=1440, description="Min encounter duration (minutes)")
    ] = 10,
    search_radius_nm: Annotated[
        float, Query(ge=1, le=100, description="Radius to search for nearby vessels (nm)")
    ] = 5.0,
) -> dict[str, Any]:
    """Detect encounters for a specific vessel.

    Finds other vessels that came within range of the target vessel.
    """
    encounters = await detect_encounters_for_vessel(
        mmsi=mmsi,
        time_start=time_start,
        time_end=time_end,
        distance_threshold_nm=distance_threshold_nm,
        min_duration_minutes=min_duration_minutes,
        search_radius_nm=search_radius_nm,
    )

    return {
        "mmsi": str(mmsi),
        "total_encounters": len(encounters),
        "encounters": [e.to_dict() for e in encounters],
    }


# ---------------------------------------------------------------------------
# Voyage reconstruction
# ---------------------------------------------------------------------------


@router.get("/voyages/{mmsi}")
async def get_voyages(
    mmsi: int,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    max_waypoints: Annotated[int, Query(ge=10, le=1000, description="Max waypoints per voyage")] = 200,
) -> dict[str, Any]:
    """Reconstruct port-to-port voyages for a vessel.

    Detects port stays, extracts voyage segments between them, simplifies
    tracks to waypoints, and computes distance/speed metrics.
    """
    voyages = await reconstruct_vessel_voyages(
        mmsi=mmsi,
        time_start=time_start,
        time_end=time_end,
        max_waypoints=max_waypoints,
    )

    # Summary
    total_distance = sum(v.distance_nm for v in voyages)
    total_hours = sum(v.duration_hours for v in voyages)
    completed = sum(1 for v in voyages if v.status.value == "completed")
    in_progress = sum(1 for v in voyages if v.status.value == "in_progress")

    return {
        "mmsi": str(mmsi),
        "total_voyages": len(voyages),
        "completed": completed,
        "in_progress": in_progress,
        "total_distance_nm": round(total_distance, 2),
        "total_duration_hours": round(total_hours, 2),
        "voyages": [v.to_dict() for v in voyages],
    }
