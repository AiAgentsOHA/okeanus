"""Composite vessel risk scoring engine.

Combines multiple risk factors (flag state, AIS gaps, behavior,
encounters, geofence violations, identity) into a single 0-100
composite risk score with classification and evidence trail.

Usage:
    score = await score_vessel(mmsi=123456789)
    score.composite_score  # 0-100
    score.risk_level       # LOW / MEDIUM / HIGH / CRITICAL
    score.factors          # list of individual RiskFactor results
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from okeanus.ml.risk.factors import (
    RiskFactor,
    RiskLevel,
    calc_ais_gap_risk,
    calc_behavioral_risk,
    calc_encounter_risk,
    calc_flag_state_risk,
    calc_geofence_risk,
    calc_identity_risk,
)

logger = logging.getLogger(__name__)

# Default factor weights — must sum to 1.0
DEFAULT_WEIGHTS: dict[str, float] = {
    "flag_state": 0.15,
    "ais_gap": 0.20,
    "behavioral": 0.20,
    "encounter": 0.15,
    "geofence": 0.15,
    "identity": 0.15,
}

# Composite score → risk level thresholds
RISK_THRESHOLDS: list[tuple[float, RiskLevel]] = [
    (75.0, RiskLevel.CRITICAL),
    (50.0, RiskLevel.HIGH),
    (25.0, RiskLevel.MEDIUM),
    (0.0, RiskLevel.LOW),
]

# All available factor calculators
FACTOR_CALCULATORS = {
    "flag_state": calc_flag_state_risk,
    "ais_gap": calc_ais_gap_risk,
    "behavioral": calc_behavioral_risk,
    "encounter": calc_encounter_risk,
    "geofence": calc_geofence_risk,
    "identity": calc_identity_risk,
}


@dataclass
class VesselRiskScore:
    """Complete risk assessment for a single vessel."""

    mmsi: int
    composite_score: float  # 0-100
    risk_level: RiskLevel
    factors: list[RiskFactor]
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    vessel_info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mmsi": self.mmsi,
            "composite_score": round(self.composite_score, 2),
            "risk_level": self.risk_level.value,
            "scored_at": self.scored_at.isoformat(),
            "vessel_info": self.vessel_info,
            "factors": [f.to_dict() for f in self.factors],
            "summary": self._summary(),
        }

    def _summary(self) -> str:
        """Human-readable risk summary."""
        top_factors = sorted(self.factors, key=lambda f: f.score, reverse=True)
        top = [f for f in top_factors if f.score > 0.2]
        if not top:
            return f"MMSI {self.mmsi}: Low risk — no significant risk indicators."
        parts = [f"{f.name} ({f.score:.0%})" for f in top[:3]]
        return (
            f"MMSI {self.mmsi}: {self.risk_level.value.upper()} risk "
            f"(score {self.composite_score:.0f}/100). "
            f"Key factors: {', '.join(parts)}."
        )


def _classify_risk(score: float) -> RiskLevel:
    """Map composite score to risk level."""
    for threshold, level in RISK_THRESHOLDS:
        if score >= threshold:
            return level
    return RiskLevel.LOW


async def score_vessel(
    mmsi: int,
    *,
    weights: dict[str, float] | None = None,
    include_factors: list[str] | None = None,
    positions: list[dict[str, Any]] | None = None,
    trajectory_segments: list[dict[str, Any]] | None = None,
    encounters: list[dict[str, Any]] | None = None,
    alerts: list[dict[str, Any]] | None = None,
    vessel_info: dict[str, Any] | None = None,
    flag_override: str | None = None,
) -> VesselRiskScore:
    """Compute composite risk score for a vessel.

    All factor calculations run concurrently for speed.  Pre-computed
    data can be passed in to avoid redundant DB queries.

    Args:
        mmsi: Vessel MMSI identifier.
        weights: Override default factor weights (must sum to 1.0).
        include_factors: Only evaluate these factors (default: all).
        positions: Pre-fetched AIS positions (for ais_gap, identity).
        trajectory_segments: Pre-computed trajectory segments.
        encounters: Pre-computed encounter list.
        alerts: Pre-fetched geofence alerts.
        vessel_info: Pre-fetched vessel static info.
        flag_override: ISO-2 flag state override.

    Returns:
        VesselRiskScore with composite score, level, and per-factor detail.
    """
    w = weights or DEFAULT_WEIGHTS
    active_factors = include_factors or list(FACTOR_CALCULATORS.keys())

    # Build coroutines for each requested factor
    kwargs = {
        "mmsi": mmsi,
        "positions": positions,
        "trajectory_segments": trajectory_segments,
        "encounters": encounters,
        "alerts": alerts,
        "vessel_info": vessel_info,
        "flag_override": flag_override,
    }

    tasks: dict[str, Any] = {}
    for name in active_factors:
        calc = FACTOR_CALCULATORS.get(name)
        if calc is None:
            logger.warning("Unknown risk factor: %s", name)
            continue
        tasks[name] = calc(**kwargs)

    # Run all factor calculations concurrently
    results: list[RiskFactor] = []
    if tasks:
        factor_results = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )
        for name, result in zip(tasks.keys(), factor_results):
            if isinstance(result, Exception):
                logger.error("Risk factor %s failed: %s", name, result)
                results.append(RiskFactor(
                    name=name,
                    score=0.0,
                    weight=w.get(name, 0.1),
                    evidence=[f"Factor calculation failed: {result}"],
                ))
            else:
                # Override weight from config
                result.weight = w.get(name, result.weight)
                results.append(result)

    # Compute weighted composite score (0-100)
    total_weight = sum(f.weight for f in results)
    if total_weight > 0:
        weighted_sum = sum(f.score * f.weight for f in results)
        composite = (weighted_sum / total_weight) * 100
    else:
        composite = 0.0

    risk_level = _classify_risk(composite)

    return VesselRiskScore(
        mmsi=mmsi,
        composite_score=composite,
        risk_level=risk_level,
        factors=results,
        vessel_info=vessel_info or {},
    )


async def score_fleet(
    mmsis: list[int],
    *,
    weights: dict[str, float] | None = None,
    include_factors: list[str] | None = None,
    max_concurrent: int = 10,
) -> list[VesselRiskScore]:
    """Score multiple vessels concurrently.

    Uses a semaphore to limit concurrent DB connections.
    """
    sem = asyncio.Semaphore(max_concurrent)

    async def _score_one(mmsi: int) -> VesselRiskScore:
        async with sem:
            return await score_vessel(
                mmsi, weights=weights, include_factors=include_factors
            )

    return await asyncio.gather(*[_score_one(m) for m in mmsis])


def get_factor_descriptions() -> list[dict[str, Any]]:
    """Return metadata about all available risk factors."""
    descriptions = {
        "flag_state": {
            "name": "Flag State Risk",
            "description": (
                "Evaluates the vessel's flag state against the IUU Fishing Index. "
                "Flags of convenience and states with poor fisheries enforcement "
                "receive higher risk scores."
            ),
            "data_sources": ["IUU Fishing Index", "MMSI MID table"],
            "default_weight": DEFAULT_WEIGHTS["flag_state"],
        },
        "ais_gap": {
            "name": "AIS Gap Risk",
            "description": (
                "Detects extended AIS transmission gaps that may indicate "
                "intentional dark activity (transponder switched off). "
                "Gaps >6h are suspicious, >24h are critical."
            ),
            "data_sources": ["AIS position history"],
            "default_weight": DEFAULT_WEIGHTS["ais_gap"],
        },
        "behavioral": {
            "name": "Behavioral Risk",
            "description": (
                "Analyzes vessel movement patterns for suspicious activity: "
                "fishing in unexpected areas, excessive loitering, evasive "
                "maneuvering, speed anomalies."
            ),
            "data_sources": ["Trajectory classification engine"],
            "default_weight": DEFAULT_WEIGHTS["behavioral"],
        },
        "encounter": {
            "name": "Encounter Risk",
            "description": (
                "Evaluates vessel-to-vessel meetings for STS transfer patterns, "
                "suspicious rendezvous events, and associations with high-risk "
                "vessels."
            ),
            "data_sources": ["Encounter detection engine"],
            "default_weight": DEFAULT_WEIGHTS["encounter"],
        },
        "geofence": {
            "name": "Geofence Violation Risk",
            "description": (
                "Checks vessel history for unauthorized entry into Marine "
                "Protected Areas, restricted zones, sanctioned waters, or "
                "speed violations in traffic schemes."
            ),
            "data_sources": ["Geofence alert history"],
            "default_weight": DEFAULT_WEIGHTS["geofence"],
        },
        "identity": {
            "name": "Identity Risk",
            "description": (
                "Examines vessel identity for anomalies: non-standard MMSI, "
                "missing IMO for SOLAS vessels, suspicious names, and "
                "ship-type vs behavior inconsistencies."
            ),
            "data_sources": ["AIS static data", "MMSI registry"],
            "default_weight": DEFAULT_WEIGHTS["identity"],
        },
    }
    return [
        {"key": k, **v}
        for k, v in descriptions.items()
        if k in FACTOR_CALCULATORS
    ]
