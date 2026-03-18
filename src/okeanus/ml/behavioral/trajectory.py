"""Trajectory classification engine.

Classifies vessel behaviour from AIS position sequences into:
- anchored: effectively stationary (SOG < 0.5 kn)
- loitering: low speed with high heading variance (drifting in circles)
- fishing: characteristic speed/turn patterns (trawl, longline, purse-seine)
- transiting: steady speed on a consistent course
- drifting: low speed, low heading variance, no purposeful movement
- maneuvering: frequent speed/course changes (port approach, channel navigation)

Each classification includes a confidence score and supporting kinematic evidence.
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select

from okeanus.db.postgres import async_session_factory
from okeanus.schema.vessel import VesselObservation

logger = logging.getLogger(__name__)


class BehaviorType(str, Enum):
    ANCHORED = "anchored"
    LOITERING = "loitering"
    FISHING = "fishing"
    TRANSITING = "transiting"
    DRIFTING = "drifting"
    MANEUVERING = "maneuvering"
    UNKNOWN = "unknown"


@dataclass
class TrackPoint:
    """Single AIS position with kinematics."""

    timestamp: datetime
    lon: float
    lat: float
    sog: float  # knots
    cog: float  # degrees
    heading: int | None
    mmsi: int
    nav_status: int | None = None


@dataclass
class TrajectorySegment:
    """A classified segment of vessel track."""

    segment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mmsi: int = 0
    behavior: BehaviorType = BehaviorType.UNKNOWN
    confidence: float = 0.0
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: float = 0.0
    point_count: int = 0
    # Kinematic summary
    mean_sog: float = 0.0
    std_sog: float = 0.0
    mean_cog: float = 0.0
    cog_variance: float = 0.0  # circular variance [0, 1]
    heading_rate: float = 0.0  # degrees/minute
    sinuosity: float = 0.0  # path_length / straight_line_distance
    distance_nm: float = 0.0  # total distance in nautical miles
    # Bounding box
    bbox: list[float] = field(default_factory=list)  # [west, south, east, north]

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "mmsi": str(self.mmsi),
            "behavior": self.behavior.value,
            "confidence": round(self.confidence, 3),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": round(self.duration_minutes, 1),
            "point_count": self.point_count,
            "kinematics": {
                "mean_sog_kn": round(self.mean_sog, 2),
                "std_sog_kn": round(self.std_sog, 2),
                "cog_variance": round(self.cog_variance, 4),
                "heading_rate_deg_min": round(self.heading_rate, 2),
                "sinuosity": round(self.sinuosity, 3),
                "distance_nm": round(self.distance_nm, 2),
            },
            "bbox": self.bbox,
        }


# ---------------------------------------------------------------------------
# Geodesic helpers
# ---------------------------------------------------------------------------

def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    R_NM = 3440.065  # Earth radius in nautical miles
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(a))


def _circular_variance(angles_deg: list[float]) -> float:
    """Circular variance of angles in [0, 1].  0 = all same, 1 = uniform spread."""
    if len(angles_deg) < 2:
        return 0.0
    sin_sum = sum(math.sin(math.radians(a)) for a in angles_deg)
    cos_sum = sum(math.cos(math.radians(a)) for a in angles_deg)
    n = len(angles_deg)
    r_bar = math.sqrt(sin_sum**2 + cos_sum**2) / n
    return 1.0 - r_bar


def _mean_std(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    mean = sum(vals) / len(vals)
    if len(vals) < 2:
        return mean, 0.0
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return mean, math.sqrt(var)


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------

# Thresholds (tunable via config in future)
_ANCHORED_SOG = 0.5        # knots
_LOITER_SOG_MAX = 2.0      # knots
_LOITER_COG_VAR = 0.4      # circular variance
_FISHING_SOG_MIN = 1.5     # knots
_FISHING_SOG_MAX = 5.0     # knots
_FISHING_COG_VAR = 0.25    # high turn rate
_FISHING_SINUOSITY = 1.5   # path much longer than straight line
_TRANSIT_SOG_MIN = 4.0     # knots
_TRANSIT_COG_VAR_MAX = 0.15  # low course variance
_DRIFT_SOG_MAX = 3.0       # knots
_DRIFT_COG_VAR_MAX = 0.15  # steady drift direction
_MANEUVER_HEADING_RATE = 3.0  # degrees/minute


def _compute_kinematics(points: list[TrackPoint]) -> dict[str, float]:
    """Compute kinematic features from a sequence of track points."""
    sogs = [p.sog for p in points if p.sog is not None]
    cogs = [p.cog for p in points if p.cog is not None]

    mean_sog, std_sog = _mean_std(sogs)
    cog_var = _circular_variance(cogs)

    # Total path distance
    path_dist = 0.0
    for i in range(1, len(points)):
        path_dist += _haversine_nm(
            points[i - 1].lat, points[i - 1].lon,
            points[i].lat, points[i].lon,
        )

    # Straight-line distance
    if len(points) >= 2:
        straight = _haversine_nm(
            points[0].lat, points[0].lon,
            points[-1].lat, points[-1].lon,
        )
    else:
        straight = 0.0

    sinuosity = path_dist / straight if straight > 0.01 else (1.0 if path_dist < 0.01 else 99.0)

    # Heading rate of turn (mean absolute change per minute)
    heading_rates: list[float] = []
    for i in range(1, len(points)):
        if points[i].heading is not None and points[i - 1].heading is not None:
            dt = (points[i].timestamp - points[i - 1].timestamp).total_seconds()
            if dt > 0:
                dh = abs(points[i].heading - points[i - 1].heading)
                if dh > 180:
                    dh = 360 - dh
                heading_rates.append(dh / (dt / 60.0))

    mean_heading_rate = sum(heading_rates) / len(heading_rates) if heading_rates else 0.0

    # Duration
    if len(points) >= 2:
        duration = (points[-1].timestamp - points[0].timestamp).total_seconds() / 60.0
    else:
        duration = 0.0

    # Bounding box
    lats = [p.lat for p in points]
    lons = [p.lon for p in points]

    return {
        "mean_sog": mean_sog,
        "std_sog": std_sog,
        "cog_variance": cog_var,
        "heading_rate": mean_heading_rate,
        "sinuosity": sinuosity,
        "path_distance_nm": path_dist,
        "duration_minutes": duration,
        "bbox": [min(lons), min(lats), max(lons), max(lats)],
    }


def classify_segment(points: list[TrackPoint]) -> TrajectorySegment:
    """Classify a sequence of AIS positions into a behaviour type."""
    if len(points) < 2:
        return TrajectorySegment(
            mmsi=points[0].mmsi if points else 0,
            behavior=BehaviorType.UNKNOWN,
            confidence=0.0,
            point_count=len(points),
        )

    kin = _compute_kinematics(points)
    seg = TrajectorySegment(
        mmsi=points[0].mmsi,
        start_time=points[0].timestamp,
        end_time=points[-1].timestamp,
        duration_minutes=kin["duration_minutes"],
        point_count=len(points),
        mean_sog=kin["mean_sog"],
        std_sog=kin["std_sog"],
        cog_variance=kin["cog_variance"],
        heading_rate=kin["heading_rate"],
        sinuosity=kin["sinuosity"],
        distance_nm=kin["path_distance_nm"],
        bbox=kin["bbox"],
    )

    # --- Decision tree ---
    # Priority order: anchored > fishing > loitering > maneuvering > transiting > drifting

    # 1. Anchored: nearly zero speed
    if kin["mean_sog"] < _ANCHORED_SOG:
        seg.behavior = BehaviorType.ANCHORED
        seg.confidence = min(1.0, (1.0 - kin["mean_sog"] / _ANCHORED_SOG) * 0.5 + 0.5)
        return seg

    # 2. Fishing: moderate speed + high course variance + sinuous path
    fishing_score = 0.0
    if _FISHING_SOG_MIN <= kin["mean_sog"] <= _FISHING_SOG_MAX:
        fishing_score += 0.35
    if kin["cog_variance"] >= _FISHING_COG_VAR:
        fishing_score += 0.35
    if kin["sinuosity"] >= _FISHING_SINUOSITY:
        fishing_score += 0.30

    if fishing_score >= 0.65:
        seg.behavior = BehaviorType.FISHING
        seg.confidence = min(1.0, fishing_score)
        return seg

    # 3. Loitering: slow + spinning
    if kin["mean_sog"] < _LOITER_SOG_MAX and kin["cog_variance"] >= _LOITER_COG_VAR:
        seg.behavior = BehaviorType.LOITERING
        seg.confidence = min(1.0, 0.5 + kin["cog_variance"] * 0.5)
        return seg

    # 4. Maneuvering: high heading rate of turn
    if kin["heading_rate"] >= _MANEUVER_HEADING_RATE:
        seg.behavior = BehaviorType.MANEUVERING
        seg.confidence = min(1.0, kin["heading_rate"] / (_MANEUVER_HEADING_RATE * 2))
        return seg

    # 5. Transiting: fast + steady course
    if kin["mean_sog"] >= _TRANSIT_SOG_MIN and kin["cog_variance"] <= _TRANSIT_COG_VAR_MAX:
        seg.behavior = BehaviorType.TRANSITING
        seg.confidence = min(1.0, 0.5 + (1.0 - kin["cog_variance"]) * 0.3 + min(kin["mean_sog"] / 15.0, 0.2))
        return seg

    # 6. Drifting: slow + steady direction
    if kin["mean_sog"] < _DRIFT_SOG_MAX and kin["cog_variance"] <= _DRIFT_COG_VAR_MAX:
        seg.behavior = BehaviorType.DRIFTING
        seg.confidence = 0.5
        return seg

    # Fallback
    seg.behavior = BehaviorType.UNKNOWN
    seg.confidence = 0.2
    return seg


# ---------------------------------------------------------------------------
# Segmentation: split a track into behaviour windows
# ---------------------------------------------------------------------------

def segment_track(
    points: list[TrackPoint],
    window_minutes: int = 30,
    step_minutes: int = 15,
) -> list[TrajectorySegment]:
    """Sliding-window segmentation + classification of a vessel track.

    Args:
        points: Chronologically sorted AIS positions for one vessel.
        window_minutes: Classification window duration.
        step_minutes: Step size for the sliding window.

    Returns:
        List of classified trajectory segments.
    """
    if len(points) < 3:
        return [classify_segment(points)] if points else []

    segments: list[TrajectorySegment] = []
    window_td = timedelta(minutes=window_minutes)
    step_td = timedelta(minutes=step_minutes)

    cursor = points[0].timestamp
    end_time = points[-1].timestamp

    while cursor <= end_time:
        window_end = cursor + window_td
        window_points = [p for p in points if cursor <= p.timestamp <= window_end]

        if len(window_points) >= 3:
            seg = classify_segment(window_points)
            segments.append(seg)

        cursor += step_td

    # Merge consecutive identical behaviours
    return _merge_segments(segments)


def _merge_segments(segments: list[TrajectorySegment]) -> list[TrajectorySegment]:
    """Merge consecutive segments with the same behaviour classification."""
    if not segments:
        return []

    merged: list[TrajectorySegment] = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        if prev.behavior == seg.behavior:
            # Extend the previous segment
            prev.end_time = seg.end_time
            prev.duration_minutes = (
                (prev.end_time - prev.start_time).total_seconds() / 60.0
                if prev.start_time and prev.end_time
                else prev.duration_minutes
            )
            prev.point_count += seg.point_count
            prev.distance_nm += seg.distance_nm
            prev.confidence = (prev.confidence + seg.confidence) / 2
            # Expand bbox
            if prev.bbox and seg.bbox:
                prev.bbox = [
                    min(prev.bbox[0], seg.bbox[0]),
                    min(prev.bbox[1], seg.bbox[1]),
                    max(prev.bbox[2], seg.bbox[2]),
                    max(prev.bbox[3], seg.bbox[3]),
                ]
        else:
            merged.append(seg)

    return merged


# ---------------------------------------------------------------------------
# Database query helper
# ---------------------------------------------------------------------------

async def classify_vessel_track(
    mmsi: int,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
    window_minutes: int = 30,
    step_minutes: int = 15,
) -> list[TrajectorySegment]:
    """Fetch AIS positions for a vessel and classify trajectory segments.

    Queries the observations table for vessel positions, converts to
    TrackPoints, runs sliding-window classification, and returns segments.
    """
    from shapely import wkb as shapely_wkb

    stmt = select(VesselObservation).where(
        VesselObservation.mmsi == mmsi,
    ).order_by(VesselObservation.timestamp)

    if time_start:
        stmt = stmt.where(VesselObservation.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(VesselObservation.timestamp <= time_end)

    stmt = stmt.limit(10_000)

    points: list[TrackPoint] = []
    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()
        for r in rows:
            # Extract lat/lon from PostGIS geometry while session is open
            try:
                geom = shapely_wkb.loads(bytes(r.geometry.data))
                lon, lat = geom.x, geom.y
            except Exception:
                continue

            points.append(TrackPoint(
                timestamp=r.timestamp,
                lon=lon,
                lat=lat,
                sog=r.sog or 0.0,
                cog=r.cog or 0.0,
                heading=r.heading,
                mmsi=mmsi,
                nav_status=r.nav_status,
            ))

    if not points:
        return []

    return segment_track(points, window_minutes, step_minutes)
