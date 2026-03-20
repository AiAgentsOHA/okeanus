"""Report generation orchestrator.

Gathers data from multiple subsystems (risk, behavioral, voyages,
encounters) and renders them into HTML intelligence reports.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from okeanus.reports.templates import (
    render_area_report,
    render_encounter_report,
    render_risk_report,
    render_vessel_profile,
)

logger = logging.getLogger(__name__)


async def generate_risk_report(mmsi: int) -> str:
    """Generate a full risk assessment HTML report for a vessel."""
    from okeanus.ml.risk.scoring import score_vessel

    score = await score_vessel(mmsi=mmsi)
    return render_risk_report(score.to_dict())


async def generate_vessel_profile(mmsi: int) -> str:
    """Generate a comprehensive vessel profile HTML report.

    Aggregates: identity, risk score, trajectory, voyages, encounters.
    """
    import asyncio

    from okeanus.ml.risk.scoring import score_vessel

    # Gather all data concurrently
    risk_task = score_vessel(mmsi=mmsi)
    trajectory_task = _get_trajectory(mmsi)
    voyage_task = _get_voyages(mmsi)
    encounter_task = _get_encounters(mmsi)
    info_task = _get_vessel_info(mmsi)

    risk_result, trajectory_data, voyage_data, encounter_data, vessel_info = (
        await asyncio.gather(
            risk_task,
            trajectory_task,
            voyage_task,
            encounter_task,
            info_task,
            return_exceptions=True,
        )
    )

    # Handle exceptions gracefully
    if isinstance(risk_result, Exception):
        logger.error("Risk scoring failed for %s: %s", mmsi, risk_result)
        risk_data = None
    else:
        risk_data = risk_result.to_dict()

    if isinstance(vessel_info, Exception):
        vessel_info = {}

    return render_vessel_profile(
        mmsi=mmsi,
        vessel_info=vessel_info if isinstance(vessel_info, dict) else {},
        risk_data=risk_data,
        trajectory_data=trajectory_data if isinstance(trajectory_data, dict) else None,
        voyage_data=voyage_data if isinstance(voyage_data, dict) else None,
        encounter_data=encounter_data if isinstance(encounter_data, dict) else None,
    )


async def generate_area_report(
    bbox: tuple[float, float, float, float],
    time_start: datetime,
    time_end: datetime,
) -> str:
    """Generate an area activity intelligence report."""
    import asyncio

    # Gather area data concurrently
    encounters_task = _get_area_encounters(bbox, time_start, time_end)
    vessels_task = _get_area_vessels(bbox, time_start, time_end)

    encounters_result, vessels_result = await asyncio.gather(
        encounters_task, vessels_task, return_exceptions=True
    )

    encounters = encounters_result if isinstance(encounters_result, list) else []
    vessel_mmsis = vessels_result if isinstance(vessels_result, list) else []

    # Score detected vessels
    risk_scores: list[dict[str, Any]] = []
    if vessel_mmsis:
        from okeanus.ml.risk.scoring import score_fleet

        try:
            scores = await score_fleet(
                mmsis=vessel_mmsis[:50], max_concurrent=5
            )
            risk_scores = [s.to_dict() for s in scores]
        except Exception as exc:
            logger.error("Fleet scoring failed: %s", exc)

    return render_area_report(
        bbox=bbox,
        vessel_count=len(vessel_mmsis),
        encounters=encounters,
        risk_scores=risk_scores,
        time_start=time_start.isoformat(),
        time_end=time_end.isoformat(),
    )


async def generate_encounter_report(encounter_data: dict[str, Any]) -> str:
    """Generate a detailed encounter analysis report."""
    return render_encounter_report(encounter_data)


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------


async def _get_trajectory(mmsi: int) -> dict[str, Any]:
    """Fetch trajectory classification data."""
    try:
        from okeanus.ml.behavioral.trajectory import classify_vessel_track

        segments = await classify_vessel_track(mmsi=mmsi, window_minutes=60)
        total_minutes = sum(s.duration_minutes for s in segments)
        behavior_summary: dict[str, Any] = {}
        for seg in segments:
            b = seg.behavior.value
            behavior_summary[b] = behavior_summary.get(b, {"minutes": 0.0})
            behavior_summary[b]["minutes"] += seg.duration_minutes

        for b, stats in behavior_summary.items():
            stats["percentage"] = (
                round(stats["minutes"] / total_minutes * 100, 1)
                if total_minutes > 0
                else 0
            )

        return {
            "segments": [s.to_dict() for s in segments],
            "behavior_summary": behavior_summary,
            "total_minutes": total_minutes,
        }
    except Exception as exc:
        logger.debug("Trajectory fetch failed for %s: %s", mmsi, exc)
        return {}


async def _get_voyages(mmsi: int) -> dict[str, Any]:
    """Fetch voyage reconstruction data."""
    try:
        from okeanus.ml.behavioral.voyages import reconstruct_vessel_voyages

        voyages = await reconstruct_vessel_voyages(mmsi=mmsi)
        return {
            "voyages": [v.to_dict() for v in voyages],
            "total_voyages": len(voyages),
        }
    except Exception as exc:
        logger.debug("Voyage fetch failed for %s: %s", mmsi, exc)
        return {}


async def _get_encounters(mmsi: int) -> dict[str, Any]:
    """Fetch encounter history."""
    try:
        from okeanus.ml.behavioral.encounters import detect_encounters_for_vessel

        encounters = await detect_encounters_for_vessel(mmsi=mmsi)
        return {
            "encounters": [e.to_dict() for e in encounters],
            "total": len(encounters),
        }
    except Exception as exc:
        logger.debug("Encounter fetch failed for %s: %s", mmsi, exc)
        return {}


async def _get_vessel_info(mmsi: int) -> dict[str, Any]:
    """Fetch vessel static information."""
    from okeanus.ml.risk.factors import SHIP_TYPE_MAP, _mmsi_to_flag

    try:
        from okeanus.db.postgres import async_session
        from okeanus.schema.vessel import VesselObservation

        from sqlalchemy import select

        async with async_session() as session:
            stmt = (
                select(VesselObservation)
                .where(VesselObservation.mmsi == mmsi)
                .order_by(VesselObservation.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                ship_type = row.ship_type
                type_name = SHIP_TYPE_MAP.get(ship_type, ("Unknown", 0))[0] if ship_type else "Unknown"
                return {
                    "mmsi": mmsi,
                    "imo": row.imo,
                    "vessel_name": row.vessel_name,
                    "call_sign": row.call_sign,
                    "ship_type": ship_type,
                    "ship_type_name": type_name,
                    "flag": _mmsi_to_flag(mmsi),
                    "destination": row.destination,
                    "draught": row.draught,
                }
    except Exception as exc:
        logger.debug("Vessel info fetch failed for %s: %s", mmsi, exc)

    return {
        "mmsi": mmsi,
        "flag": _mmsi_to_flag(mmsi),
        "vessel_name": "Unknown",
    }


async def _get_area_encounters(
    bbox: tuple[float, float, float, float],
    time_start: datetime,
    time_end: datetime,
) -> list[dict[str, Any]]:
    """Fetch encounters in an area."""
    try:
        from okeanus.ml.behavioral.encounters import detect_encounters_in_area

        encounters = await detect_encounters_in_area(
            bbox=bbox, time_start=time_start, time_end=time_end
        )
        return [e.to_dict() for e in encounters]
    except Exception as exc:
        logger.debug("Area encounter fetch failed: %s", exc)
        return []


async def _get_area_vessels(
    bbox: tuple[float, float, float, float],
    time_start: datetime,
    time_end: datetime,
) -> list[int]:
    """Fetch unique vessel MMSIs in an area and time range."""
    try:
        from okeanus.db.postgres import async_session
        from okeanus.schema.vessel import VesselObservation

        from sqlalchemy import distinct, func, select

        w, s, e, n = bbox
        async with async_session() as session:
            stmt = (
                select(distinct(VesselObservation.mmsi))
                .where(
                    VesselObservation.mmsi.isnot(None),
                    VesselObservation.timestamp >= time_start,
                    VesselObservation.timestamp <= time_end,
                    func.ST_Within(
                        VesselObservation.geometry,
                        func.ST_MakeEnvelope(w, s, e, n, 4326),
                    ),
                )
                .limit(200)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]
    except Exception as exc:
        logger.debug("Area vessel fetch failed: %s", exc)
        return []
