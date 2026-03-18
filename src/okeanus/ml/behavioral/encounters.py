"""Vessel encounter and rendezvous detection.

Detects when two or more vessels come within close proximity, indicating
potential transshipment, ship-to-ship (STS) transfer, or coordinated activity.

Encounter types:
- rendezvous: Both vessels stationary/slow, high transshipment risk
- parallel_transit: Both moving in the same direction at similar speed
- crossing: Brief close approach at different headings
- loitering_pair: Both loitering in the same area
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select, text

from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation
from okeanus.schema.vessel import VesselObservation

logger = logging.getLogger(__name__)


class EncounterType(str, Enum):
    RENDEZVOUS = "rendezvous"
    PARALLEL_TRANSIT = "parallel_transit"
    CROSSING = "crossing"
    LOITERING_PAIR = "loitering_pair"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EncounterEvent:
    """A detected encounter between two vessels."""

    encounter_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    vessel_a_mmsi: int = 0
    vessel_b_mmsi: int = 0
    encounter_type: EncounterType = EncounterType.UNKNOWN
    risk_level: RiskLevel = RiskLevel.LOW
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: float = 0.0
    min_distance_nm: float = 0.0
    mean_distance_nm: float = 0.0
    # Location (centroid of encounter)
    lat: float = 0.0
    lon: float = 0.0
    # Vessel kinematics during encounter
    vessel_a_mean_sog: float = 0.0
    vessel_b_mean_sog: float = 0.0
    # Confidence and evidence
    confidence: float = 0.0
    indicators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "vessel_a_mmsi": str(self.vessel_a_mmsi),
            "vessel_b_mmsi": str(self.vessel_b_mmsi),
            "encounter_type": self.encounter_type.value,
            "risk_level": self.risk_level.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": round(self.duration_minutes, 1),
            "min_distance_nm": round(self.min_distance_nm, 3),
            "mean_distance_nm": round(self.mean_distance_nm, 3),
            "location": {"lat": round(self.lat, 5), "lon": round(self.lon, 5)},
            "vessel_a_mean_sog": round(self.vessel_a_mean_sog, 2),
            "vessel_b_mean_sog": round(self.vessel_b_mean_sog, 2),
            "confidence": round(self.confidence, 3),
            "indicators": self.indicators,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    R_NM = 3440.065
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(min(a, 1.0)))


def _angle_diff(a: float, b: float) -> float:
    """Smallest angle difference in degrees."""
    d = abs(a - b) % 360
    return d if d <= 180 else 360 - d


# ---------------------------------------------------------------------------
# Encounter detection
# ---------------------------------------------------------------------------

# Thresholds
_ENCOUNTER_DIST_NM = 0.5       # 0.5 nm ~ 926m
_ENCOUNTER_MIN_DURATION = 10    # minutes
_RENDEZVOUS_SOG_MAX = 3.0      # knots
_PARALLEL_COG_DIFF_MAX = 20.0  # degrees
_PARALLEL_SOG_RATIO_MIN = 0.7  # min(sog_a,sog_b)/max(sog_a,sog_b)


@dataclass
class _PositionRecord:
    """Internal position for encounter matching."""
    mmsi: int
    timestamp: datetime
    lat: float
    lon: float
    sog: float
    cog: float


def _classify_encounter(
    positions_a: list[_PositionRecord],
    positions_b: list[_PositionRecord],
    distances: list[float],
) -> tuple[EncounterType, RiskLevel, float, list[str]]:
    """Classify an encounter based on vessel kinematics."""
    sogs_a = [p.sog for p in positions_a]
    sogs_b = [p.sog for p in positions_b]
    mean_sog_a = sum(sogs_a) / len(sogs_a) if sogs_a else 0
    mean_sog_b = sum(sogs_b) / len(sogs_b) if sogs_b else 0
    min_dist = min(distances) if distances else 999

    indicators: list[str] = []
    confidence = 0.5

    # Both slow → rendezvous (potential transshipment)
    if mean_sog_a < _RENDEZVOUS_SOG_MAX and mean_sog_b < _RENDEZVOUS_SOG_MAX:
        encounter_type = EncounterType.RENDEZVOUS
        indicators.append("both_vessels_slow")
        confidence = 0.7

        if min_dist < 0.1:
            indicators.append("very_close_proximity")
            confidence += 0.15
        if len(positions_a) > 5:
            indicators.append("extended_duration")
            confidence += 0.1

        # Risk assessment
        duration = (positions_a[-1].timestamp - positions_a[0].timestamp).total_seconds() / 60
        if duration > 60:
            risk = RiskLevel.CRITICAL
            indicators.append("duration_over_1h")
        elif duration > 30:
            risk = RiskLevel.HIGH
        elif min_dist < 0.1:
            risk = RiskLevel.HIGH
        else:
            risk = RiskLevel.MEDIUM

        return encounter_type, risk, min(confidence, 1.0), indicators

    # Both moving same direction at similar speed → parallel transit
    cogs_a = [p.cog for p in positions_a if p.cog is not None]
    cogs_b = [p.cog for p in positions_b if p.cog is not None]
    if cogs_a and cogs_b:
        mean_cog_diff = sum(
            _angle_diff(ca, cb) for ca, cb in zip(cogs_a, cogs_b)
        ) / min(len(cogs_a), len(cogs_b))

        max_sog = max(mean_sog_a, mean_sog_b)
        min_sog = min(mean_sog_a, mean_sog_b)
        sog_ratio = min_sog / max_sog if max_sog > 0.5 else 0.0

        if mean_cog_diff < _PARALLEL_COG_DIFF_MAX and sog_ratio > _PARALLEL_SOG_RATIO_MIN:
            indicators.append("parallel_course")
            indicators.append("similar_speed")
            return (
                EncounterType.PARALLEL_TRANSIT,
                RiskLevel.MEDIUM if min_dist < 0.2 else RiskLevel.LOW,
                0.6,
                indicators,
            )

    # Brief close pass → crossing
    duration = (positions_a[-1].timestamp - positions_a[0].timestamp).total_seconds() / 60
    if duration < 30:
        indicators.append("brief_encounter")
        return EncounterType.CROSSING, RiskLevel.LOW, 0.4, indicators

    # Both loitering
    if mean_sog_a < 2.0 and mean_sog_b < 2.0:
        indicators.append("both_loitering")
        return EncounterType.LOITERING_PAIR, RiskLevel.MEDIUM, 0.5, indicators

    return EncounterType.UNKNOWN, RiskLevel.LOW, 0.3, indicators


def detect_encounters_from_positions(
    all_positions: dict[int, list[_PositionRecord]],
    distance_threshold_nm: float = _ENCOUNTER_DIST_NM,
    min_duration_minutes: float = _ENCOUNTER_MIN_DURATION,
) -> list[EncounterEvent]:
    """Detect encounters between vessels from pre-loaded position data.

    Uses a time-bucketed approach: for each time step, find vessel pairs
    within distance threshold, then track continuous encounter windows.
    """
    mmsis = sorted(all_positions.keys())
    if len(mmsis) < 2:
        return []

    # Build time-indexed positions (1-minute buckets)
    encounters: list[EncounterEvent] = []
    active: dict[tuple[int, int], dict] = {}  # (mmsi_a, mmsi_b) → tracking state

    # Collect all timestamps across all vessels
    all_ts: set[datetime] = set()
    for positions in all_positions.values():
        for p in positions:
            # Round to nearest minute
            rounded = p.timestamp.replace(second=0, microsecond=0)
            all_ts.add(rounded)

    for ts in sorted(all_ts):
        window = timedelta(minutes=2)

        # Get positions near this timestamp for each vessel
        current: dict[int, _PositionRecord] = {}
        for mmsi, positions in all_positions.items():
            closest = min(
                (p for p in positions if abs((p.timestamp - ts).total_seconds()) < window.total_seconds()),
                key=lambda p: abs((p.timestamp - ts).total_seconds()),
                default=None,
            )
            if closest:
                current[mmsi] = closest

        # Check all pairs
        current_mmsis = sorted(current.keys())
        for i in range(len(current_mmsis)):
            for j in range(i + 1, len(current_mmsis)):
                mmsi_a, mmsi_b = current_mmsis[i], current_mmsis[j]
                pa, pb = current[mmsi_a], current[mmsi_b]
                dist = _haversine_nm(pa.lat, pa.lon, pb.lat, pb.lon)

                pair = (mmsi_a, mmsi_b)

                if dist <= distance_threshold_nm:
                    if pair not in active:
                        active[pair] = {
                            "start": ts,
                            "positions_a": [],
                            "positions_b": [],
                            "distances": [],
                        }
                    active[pair]["positions_a"].append(pa)
                    active[pair]["positions_b"].append(pb)
                    active[pair]["distances"].append(dist)
                    active[pair]["last_seen"] = ts
                else:
                    # Check if this ends an active encounter
                    if pair in active:
                        state = active.pop(pair)
                        duration = (state["last_seen"] - state["start"]).total_seconds() / 60
                        if duration >= min_duration_minutes:
                            enc = _build_encounter(pair, state)
                            if enc:
                                encounters.append(enc)

    # Finalize any remaining active encounters
    for pair, state in active.items():
        if "last_seen" in state:
            duration = (state["last_seen"] - state["start"]).total_seconds() / 60
            if duration >= min_duration_minutes:
                enc = _build_encounter(pair, state)
                if enc:
                    encounters.append(enc)

    return encounters


def _build_encounter(pair: tuple[int, int], state: dict) -> EncounterEvent | None:
    """Build an EncounterEvent from tracking state."""
    positions_a = state["positions_a"]
    positions_b = state["positions_b"]
    distances = state["distances"]

    if not positions_a or not positions_b:
        return None

    enc_type, risk, confidence, indicators = _classify_encounter(
        positions_a, positions_b, distances
    )

    # Centroid location
    all_lats = [p.lat for p in positions_a] + [p.lat for p in positions_b]
    all_lons = [p.lon for p in positions_a] + [p.lon for p in positions_b]

    sogs_a = [p.sog for p in positions_a]
    sogs_b = [p.sog for p in positions_b]

    return EncounterEvent(
        vessel_a_mmsi=pair[0],
        vessel_b_mmsi=pair[1],
        encounter_type=enc_type,
        risk_level=risk,
        start_time=state["start"],
        end_time=state.get("last_seen", state["start"]),
        duration_minutes=(state.get("last_seen", state["start"]) - state["start"]).total_seconds() / 60,
        min_distance_nm=min(distances),
        mean_distance_nm=sum(distances) / len(distances),
        lat=sum(all_lats) / len(all_lats),
        lon=sum(all_lons) / len(all_lons),
        vessel_a_mean_sog=sum(sogs_a) / len(sogs_a) if sogs_a else 0,
        vessel_b_mean_sog=sum(sogs_b) / len(sogs_b) if sogs_b else 0,
        confidence=confidence,
        indicators=indicators,
    )


# ---------------------------------------------------------------------------
# Database query helpers
# ---------------------------------------------------------------------------

async def detect_encounters_in_area(
    bbox: tuple[float, float, float, float],  # west, south, east, north
    time_start: datetime,
    time_end: datetime,
    distance_threshold_nm: float = _ENCOUNTER_DIST_NM,
    min_duration_minutes: float = _ENCOUNTER_MIN_DURATION,
    limit: int = 5000,
) -> list[EncounterEvent]:
    """Detect encounters between vessels in a geographic area and time window.

    Fetches AIS positions within the bounding box and time range, groups
    by vessel, then runs pairwise encounter detection.
    """
    from geoalchemy2.functions import ST_MakeEnvelope
    from shapely import wkb as shapely_wkb

    w, s, e, n = bbox
    stmt = select(Observation).where(
        Observation.obs_type == "vessel",
        Observation.mmsi.isnot(None),
        Observation.timestamp >= time_start,
        Observation.timestamp <= time_end,
        Observation.geometry.ST_Intersects(ST_MakeEnvelope(w, s, e, n, 4326)),
    ).order_by(Observation.mmsi, Observation.timestamp).limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    # Group by vessel
    vessel_positions: dict[int, list[_PositionRecord]] = {}
    for r in rows:
        if r.mmsi is None:
            continue
        try:
            geom = shapely_wkb.loads(bytes(r.geometry.data))
            lon, lat = geom.x, geom.y
        except Exception:
            continue

        vessel_positions.setdefault(r.mmsi, []).append(_PositionRecord(
            mmsi=r.mmsi,
            timestamp=r.timestamp,
            lat=lat,
            lon=lon,
            sog=r.sog or 0.0,
            cog=r.cog or 0.0,
        ))

    logger.info(
        "Encounter detection: %d vessels, %d positions in bbox",
        len(vessel_positions), sum(len(v) for v in vessel_positions.values()),
    )

    return detect_encounters_from_positions(
        vessel_positions,
        distance_threshold_nm=distance_threshold_nm,
        min_duration_minutes=min_duration_minutes,
    )


async def detect_encounters_for_vessel(
    mmsi: int,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
    distance_threshold_nm: float = _ENCOUNTER_DIST_NM,
    min_duration_minutes: float = _ENCOUNTER_MIN_DURATION,
    search_radius_nm: float = 5.0,
) -> list[EncounterEvent]:
    """Detect encounters for a specific vessel.

    First fetches the target vessel's track, then finds other vessels
    within search_radius_nm along the track, and runs encounter detection.
    """
    from shapely import wkb as shapely_wkb

    # Get target vessel's positions
    stmt = select(VesselObservation).where(
        VesselObservation.mmsi == mmsi,
    ).order_by(VesselObservation.timestamp)

    if time_start:
        stmt = stmt.where(VesselObservation.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(VesselObservation.timestamp <= time_end)
    stmt = stmt.limit(5000)

    target_positions: list[_PositionRecord] = []
    lats, lons = [], []
    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()
        for r in rows:
            try:
                geom = shapely_wkb.loads(bytes(r.geometry.data))
                lon, lat = geom.x, geom.y
            except Exception:
                continue
            target_positions.append(_PositionRecord(
                mmsi=mmsi, timestamp=r.timestamp, lat=lat, lon=lon,
                sog=r.sog or 0.0, cog=r.cog or 0.0,
            ))
            lats.append(lat)
            lons.append(lon)

    if not target_positions:
        return []

    # Buffer the bounding box by search radius (~1 degree ≈ 60 nm)
    buffer_deg = search_radius_nm / 60.0
    bbox = (
        min(lons) - buffer_deg,
        min(lats) - buffer_deg,
        max(lons) + buffer_deg,
        max(lats) + buffer_deg,
    )

    t_start = target_positions[0].timestamp
    t_end = target_positions[-1].timestamp

    # Get nearby vessels
    from geoalchemy2.functions import ST_MakeEnvelope

    stmt2 = select(VesselObservation).where(
        VesselObservation.mmsi.isnot(None),
        VesselObservation.mmsi != mmsi,
        VesselObservation.timestamp >= t_start,
        VesselObservation.timestamp <= t_end,
        VesselObservation.geometry.ST_Intersects(
            ST_MakeEnvelope(bbox[0], bbox[1], bbox[2], bbox[3], 4326)
        ),
    ).order_by(VesselObservation.mmsi, VesselObservation.timestamp).limit(10_000)

    all_positions: dict[int, list[_PositionRecord]] = {mmsi: target_positions}
    async with async_session_factory() as session:
        nearby_rows = (await session.execute(stmt2)).scalars().all()
        for r in nearby_rows:
            if r.mmsi is None:
                continue
            try:
                geom = shapely_wkb.loads(bytes(r.geometry.data))
                lon, lat = geom.x, geom.y
            except Exception:
                continue
            all_positions.setdefault(r.mmsi, []).append(_PositionRecord(
                mmsi=r.mmsi, timestamp=r.timestamp, lat=lat, lon=lon,
                sog=r.sog or 0.0, cog=r.cog or 0.0,
            ))

    # Run detection -- only return encounters involving target vessel
    all_encounters = detect_encounters_from_positions(
        all_positions,
        distance_threshold_nm=distance_threshold_nm,
        min_duration_minutes=min_duration_minutes,
    )

    return [
        e for e in all_encounters
        if e.vessel_a_mmsi == mmsi or e.vessel_b_mmsi == mmsi
    ]
