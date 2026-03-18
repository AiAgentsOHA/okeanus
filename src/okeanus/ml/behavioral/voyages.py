"""Voyage reconstruction -- port-to-port segment extraction from raw AIS.

Reconstructs voyages by detecting port stays (low speed in port areas)
and connecting them into departure→arrival voyage segments.

A voyage includes:
- Departure port, time, and position
- Arrival port, time, and position
- Route waypoints (simplified track)
- Distance, duration, average speed
- Stops (anchorage periods en route)
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
from okeanus.schema.base import Observation

logger = logging.getLogger(__name__)


class VoyageStatus(str, Enum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    UNKNOWN = "unknown"


class PortEventType(str, Enum):
    DEPARTURE = "departure"
    ARRIVAL = "arrival"
    ANCHOR = "anchor"


@dataclass
class PortEvent:
    """A vessel arriving at or departing from a location."""
    event_type: PortEventType
    timestamp: datetime
    lat: float
    lon: float
    sog: float = 0.0
    duration_minutes: float = 0.0  # time spent at this location

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "lat": round(self.lat, 5),
            "lon": round(self.lon, 5),
            "duration_minutes": round(self.duration_minutes, 1),
        }


@dataclass
class Waypoint:
    """A simplified track point along a voyage."""
    timestamp: datetime
    lat: float
    lon: float
    sog: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "lat": round(self.lat, 5),
            "lon": round(self.lon, 5),
            "sog": round(self.sog, 2),
        }


@dataclass
class Voyage:
    """A reconstructed port-to-port voyage."""
    voyage_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mmsi: int = 0
    status: VoyageStatus = VoyageStatus.UNKNOWN
    departure: PortEvent | None = None
    arrival: PortEvent | None = None
    # Route
    waypoints: list[Waypoint] = field(default_factory=list)
    waypoint_count: int = 0
    # Metrics
    distance_nm: float = 0.0
    duration_hours: float = 0.0
    avg_speed_kn: float = 0.0
    max_speed_kn: float = 0.0
    # Stops
    stops: list[PortEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "voyage_id": self.voyage_id,
            "mmsi": str(self.mmsi),
            "status": self.status.value,
            "departure": self.departure.to_dict() if self.departure else None,
            "arrival": self.arrival.to_dict() if self.arrival else None,
            "waypoint_count": self.waypoint_count,
            "waypoints": [w.to_dict() for w in self.waypoints],
            "metrics": {
                "distance_nm": round(self.distance_nm, 2),
                "duration_hours": round(self.duration_hours, 2),
                "avg_speed_kn": round(self.avg_speed_kn, 2),
                "max_speed_kn": round(self.max_speed_kn, 2),
            },
            "stops": [s.to_dict() for s in self.stops],
            "stop_count": len(self.stops),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R_NM = 3440.065
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * R_NM * math.asin(math.sqrt(min(a, 1.0)))


@dataclass
class _Position:
    timestamp: datetime
    lat: float
    lon: float
    sog: float


# ---------------------------------------------------------------------------
# Port stay detection
# ---------------------------------------------------------------------------

_PORT_SOG_THRESHOLD = 0.5      # knots — effectively stationary
_PORT_MIN_DURATION = 60        # minutes — must stay > 1 hour to be a "port stay"
_PORT_MAX_DRIFT_NM = 0.5      # max drift during a port stay
_SIMPLIFY_DISTANCE_NM = 1.0   # Ramer-Douglas-Peucker tolerance for waypoints


def _detect_port_stays(positions: list[_Position]) -> list[dict]:
    """Detect port stays (low-speed periods) in a position sequence.

    Returns list of dicts with start_idx, end_idx, start_time, end_time,
    lat, lon, duration_minutes.
    """
    if not positions:
        return []

    stays: list[dict] = []
    in_stay = False
    stay_start_idx = 0

    for i, pos in enumerate(positions):
        if pos.sog <= _PORT_SOG_THRESHOLD:
            if not in_stay:
                in_stay = True
                stay_start_idx = i
        else:
            if in_stay:
                # End of stay
                duration = (positions[i - 1].timestamp - positions[stay_start_idx].timestamp).total_seconds() / 60
                if duration >= _PORT_MIN_DURATION:
                    # Check drift
                    stay_positions = positions[stay_start_idx:i]
                    lats = [p.lat for p in stay_positions]
                    lons = [p.lon for p in stay_positions]
                    centroid_lat = sum(lats) / len(lats)
                    centroid_lon = sum(lons) / len(lons)

                    max_drift = max(
                        _haversine_nm(centroid_lat, centroid_lon, p.lat, p.lon)
                        for p in stay_positions
                    )

                    if max_drift <= _PORT_MAX_DRIFT_NM:
                        stays.append({
                            "start_idx": stay_start_idx,
                            "end_idx": i - 1,
                            "start_time": positions[stay_start_idx].timestamp,
                            "end_time": positions[i - 1].timestamp,
                            "lat": centroid_lat,
                            "lon": centroid_lon,
                            "duration_minutes": duration,
                        })
                in_stay = False

    # Handle stay at end of track
    if in_stay and len(positions) > stay_start_idx:
        last_idx = len(positions) - 1
        duration = (positions[last_idx].timestamp - positions[stay_start_idx].timestamp).total_seconds() / 60
        if duration >= _PORT_MIN_DURATION:
            stay_positions = positions[stay_start_idx:]
            lats = [p.lat for p in stay_positions]
            lons = [p.lon for p in stay_positions]
            centroid_lat = sum(lats) / len(lats)
            centroid_lon = sum(lons) / len(lons)
            stays.append({
                "start_idx": stay_start_idx,
                "end_idx": last_idx,
                "start_time": positions[stay_start_idx].timestamp,
                "end_time": positions[last_idx].timestamp,
                "lat": centroid_lat,
                "lon": centroid_lon,
                "duration_minutes": duration,
            })

    return stays


# ---------------------------------------------------------------------------
# Track simplification (Ramer-Douglas-Peucker)
# ---------------------------------------------------------------------------

def _perpendicular_distance_nm(
    point: _Position, line_start: _Position, line_end: _Position
) -> float:
    """Approximate perpendicular distance from a point to a great-circle line."""
    d_total = _haversine_nm(line_start.lat, line_start.lon, line_end.lat, line_end.lon)
    if d_total < 0.001:
        return _haversine_nm(point.lat, point.lon, line_start.lat, line_start.lon)

    d_start = _haversine_nm(line_start.lat, line_start.lon, point.lat, point.lon)
    d_end = _haversine_nm(line_end.lat, line_end.lon, point.lat, point.lon)

    # Use Heron's formula for triangle area
    s = (d_total + d_start + d_end) / 2
    area_sq = s * (s - d_total) * (s - d_start) * (s - d_end)
    if area_sq < 0:
        return min(d_start, d_end)
    area = math.sqrt(area_sq)
    return 2 * area / d_total if d_total > 0 else 0


def _simplify_track(
    positions: list[_Position], tolerance_nm: float = _SIMPLIFY_DISTANCE_NM
) -> list[_Position]:
    """Ramer-Douglas-Peucker simplification on geographic positions."""
    if len(positions) <= 2:
        return positions

    # Find point with maximum distance from the line start→end
    max_dist = 0.0
    max_idx = 0
    for i in range(1, len(positions) - 1):
        d = _perpendicular_distance_nm(positions[i], positions[0], positions[-1])
        if d > max_dist:
            max_dist = d
            max_idx = i

    if max_dist > tolerance_nm:
        left = _simplify_track(positions[:max_idx + 1], tolerance_nm)
        right = _simplify_track(positions[max_idx:], tolerance_nm)
        return left[:-1] + right
    else:
        return [positions[0], positions[-1]]


# ---------------------------------------------------------------------------
# Voyage reconstruction
# ---------------------------------------------------------------------------

def reconstruct_voyages(
    positions: list[_Position],
    mmsi: int,
    max_waypoints: int = 200,
) -> list[Voyage]:
    """Reconstruct voyages from a chronological sequence of positions.

    Algorithm:
    1. Detect port stays (low-speed stationary periods)
    2. Segments between consecutive port stays = voyages
    3. Simplify track to waypoints
    4. Compute distance, duration, speed metrics
    """
    stays = _detect_port_stays(positions)

    if not stays:
        # No port stays detected — entire track is a single in-progress voyage
        if len(positions) < 2:
            return []

        total_dist = sum(
            _haversine_nm(positions[i - 1].lat, positions[i - 1].lon, positions[i].lat, positions[i].lon)
            for i in range(1, len(positions))
        )
        duration_h = (positions[-1].timestamp - positions[0].timestamp).total_seconds() / 3600

        simplified = _simplify_track(positions)
        waypoints = [Waypoint(p.timestamp, p.lat, p.lon, p.sog) for p in simplified[:max_waypoints]]

        return [Voyage(
            mmsi=mmsi,
            status=VoyageStatus.IN_PROGRESS,
            departure=PortEvent(
                PortEventType.DEPARTURE, positions[0].timestamp,
                positions[0].lat, positions[0].lon, positions[0].sog,
            ),
            waypoints=waypoints,
            waypoint_count=len(waypoints),
            distance_nm=total_dist,
            duration_hours=duration_h,
            avg_speed_kn=total_dist / duration_h if duration_h > 0 else 0,
            max_speed_kn=max(p.sog for p in positions),
        )]

    voyages: list[Voyage] = []

    for i in range(len(stays) - 1):
        dep_stay = stays[i]
        arr_stay = stays[i + 1]

        # Voyage positions = from end of departure stay to start of arrival stay
        voy_positions = positions[dep_stay["end_idx"]:arr_stay["start_idx"] + 1]
        if len(voy_positions) < 2:
            continue

        # Distance
        total_dist = sum(
            _haversine_nm(
                voy_positions[j - 1].lat, voy_positions[j - 1].lon,
                voy_positions[j].lat, voy_positions[j].lon,
            )
            for j in range(1, len(voy_positions))
        )

        duration_h = (voy_positions[-1].timestamp - voy_positions[0].timestamp).total_seconds() / 3600

        # Simplify track
        simplified = _simplify_track(voy_positions)
        waypoints = [Waypoint(p.timestamp, p.lat, p.lon, p.sog) for p in simplified[:max_waypoints]]

        # Detect intermediate stops (short slowdowns that don't qualify as port stays)
        stops: list[PortEvent] = []
        slow_start = None
        for pos in voy_positions[1:-1]:
            if pos.sog < 1.0 and slow_start is None:
                slow_start = pos
            elif pos.sog >= 1.0 and slow_start is not None:
                slow_dur = (pos.timestamp - slow_start.timestamp).total_seconds() / 60
                if 15 <= slow_dur < _PORT_MIN_DURATION:
                    stops.append(PortEvent(
                        PortEventType.ANCHOR, slow_start.timestamp,
                        slow_start.lat, slow_start.lon, slow_start.sog,
                        duration_minutes=slow_dur,
                    ))
                slow_start = None

        voyages.append(Voyage(
            mmsi=mmsi,
            status=VoyageStatus.COMPLETED,
            departure=PortEvent(
                PortEventType.DEPARTURE, dep_stay["end_time"],
                dep_stay["lat"], dep_stay["lon"],
                duration_minutes=dep_stay["duration_minutes"],
            ),
            arrival=PortEvent(
                PortEventType.ARRIVAL, arr_stay["start_time"],
                arr_stay["lat"], arr_stay["lon"],
                duration_minutes=arr_stay["duration_minutes"],
            ),
            waypoints=waypoints,
            waypoint_count=len(waypoints),
            distance_nm=total_dist,
            duration_hours=duration_h,
            avg_speed_kn=total_dist / duration_h if duration_h > 0 else 0,
            max_speed_kn=max((p.sog for p in voy_positions), default=0),
            stops=stops,
        ))

    # Check if there's a voyage in progress (after the last port stay)
    last_stay = stays[-1]
    remaining = positions[last_stay["end_idx"]:]
    if len(remaining) >= 5:
        total_dist = sum(
            _haversine_nm(remaining[j - 1].lat, remaining[j - 1].lon,
                          remaining[j].lat, remaining[j].lon)
            for j in range(1, len(remaining))
        )
        # Only add if vessel actually left (moved > 1 nm)
        if total_dist > 1.0:
            duration_h = (remaining[-1].timestamp - remaining[0].timestamp).total_seconds() / 3600
            simplified = _simplify_track(remaining)
            waypoints = [Waypoint(p.timestamp, p.lat, p.lon, p.sog) for p in simplified[:max_waypoints]]

            voyages.append(Voyage(
                mmsi=mmsi,
                status=VoyageStatus.IN_PROGRESS,
                departure=PortEvent(
                    PortEventType.DEPARTURE, last_stay["end_time"],
                    last_stay["lat"], last_stay["lon"],
                    duration_minutes=last_stay["duration_minutes"],
                ),
                waypoints=waypoints,
                waypoint_count=len(waypoints),
                distance_nm=total_dist,
                duration_hours=duration_h,
                avg_speed_kn=total_dist / duration_h if duration_h > 0 else 0,
                max_speed_kn=max((p.sog for p in remaining), default=0),
            ))

    return voyages


# ---------------------------------------------------------------------------
# Database query helper
# ---------------------------------------------------------------------------

async def reconstruct_vessel_voyages(
    mmsi: int,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
    max_waypoints: int = 200,
) -> list[Voyage]:
    """Fetch AIS positions and reconstruct voyages for a vessel."""
    from shapely import wkb as shapely_wkb

    stmt = select(Observation).where(
        Observation.obs_type == "vessel",
        Observation.mmsi == mmsi,
    ).order_by(Observation.timestamp)

    if time_start:
        stmt = stmt.where(Observation.timestamp >= time_start)
    if time_end:
        stmt = stmt.where(Observation.timestamp <= time_end)

    stmt = stmt.limit(50_000)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        return []

    positions: list[_Position] = []
    for r in rows:
        try:
            geom = shapely_wkb.loads(bytes(r.geometry.data))
            lon, lat = geom.x, geom.y
        except Exception:
            continue
        positions.append(_Position(
            timestamp=r.timestamp, lat=lat, lon=lon, sog=r.sog or 0.0,
        ))

    return reconstruct_voyages(positions, mmsi, max_waypoints)
