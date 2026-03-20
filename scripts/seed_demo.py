"""Seed the database with realistic demo data across all risk engines.

Creates narrative-driven vessel scenarios that trigger every risk factor,
behavioral classification, encounter detection, and geofence alert system.

Usage:
    DATABASE_URL="postgresql+asyncpg://okeanus:okeanus@localhost:5432/okeanus" \
        python scripts/seed_demo.py

Idempotent: clears previous demo data (source_name='DEMO_SEED') before seeding.
"""

from __future__ import annotations

import asyncio
import math
import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import delete, text

from okeanus.db.postgres import async_session_factory, engine
from okeanus.geofence.models import GeofenceAlert, GeofenceRule, GeofenceZone
from okeanus.schema.base import Base, Observation
from okeanus.schema.vessel import VesselObservation

random.seed(42)
NOW = datetime.now(UTC)

# ---------------------------------------------------------------------------
# Position generation helpers
# ---------------------------------------------------------------------------

# Earth radius in nautical miles
_EARTH_NM = 3440.065


def _advance_position(
    lat: float, lon: float, heading_deg: float, speed_kn: float, minutes: float
) -> tuple[float, float]:
    """Advance a position along a great-circle bearing.

    Returns (new_lat, new_lon) after traveling at speed_kn for `minutes`.
    """
    distance_nm = speed_kn * (minutes / 60.0)
    d_rad = distance_nm / _EARTH_NM
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    brg_rad = math.radians(heading_deg)

    new_lat = math.asin(
        math.sin(lat_rad) * math.cos(d_rad)
        + math.cos(lat_rad) * math.sin(d_rad) * math.cos(brg_rad)
    )
    new_lon = lon_rad + math.atan2(
        math.sin(brg_rad) * math.sin(d_rad) * math.cos(lat_rad),
        math.cos(d_rad) - math.sin(lat_rad) * math.sin(new_lat),
    )
    return math.degrees(new_lat), math.degrees(new_lon)


def _normalize_angle(deg: float) -> float:
    """Normalize angle to [0, 360)."""
    return deg % 360.0


def _make_vessel_obs(
    mmsi: int,
    ts: datetime,
    lat: float,
    lon: float,
    sog: float,
    cog: float,
    heading: int,
    *,
    vessel_name: str = "",
    ship_type: int = 0,
    imo: int | None = None,
    call_sign: str | None = None,
    nav_status: int = 0,
    destination: str = "",
    draught: float | None = None,
    idx: int = 0,
) -> VesselObservation:
    """Create a single VesselObservation record."""
    return VesselObservation(
        id=uuid.uuid4(),
        obs_type="vessel",
        timestamp=ts,
        geometry=from_shape(Point(lon, lat), srid=4326),
        source_id=f"demo-{mmsi}-{idx:05d}",
        source_name="DEMO_SEED",
        mmsi=mmsi,
        quality_score=0.95,
        vessel_name=vessel_name,
        ship_type=ship_type,
        imo=imo,
        call_sign=call_sign,
        nav_status=nav_status,
        sog=round(sog, 1),
        cog=round(_normalize_angle(cog), 1),
        heading=int(_normalize_angle(heading)) % 360,
        destination=destination,
        draught=draught,
        created_at=NOW,
        updated_at=NOW,
    )


def generate_transit_track(
    start_lat: float,
    start_lon: float,
    heading: float,
    speed_kn: float,
    duration_hours: float,
    interval_min: int = 5,
) -> list[dict]:
    """Generate a steady transit track.

    Returns list of {lat, lon, sog, cog, heading, minutes_offset}.
    """
    positions = []
    lat, lon = start_lat, start_lon
    steps = int(duration_hours * 60 / interval_min)

    for i in range(steps):
        sog = speed_kn + random.uniform(-0.5, 0.5)
        cog = heading + random.uniform(-2, 2)
        hdg = cog + random.uniform(-3, 3)
        positions.append({
            "lat": lat, "lon": lon,
            "sog": max(0.1, sog), "cog": cog, "heading": hdg,
            "minutes_offset": i * interval_min,
        })
        lat, lon = _advance_position(lat, lon, cog, sog, interval_min)

    return positions


def generate_fishing_track(
    start_lat: float,
    start_lon: float,
    duration_hours: float,
    interval_min: int = 5,
) -> list[dict]:
    """Generate a fishing behavior track — sinuous, slow, high COG variance."""
    positions = []
    lat, lon = start_lat, start_lon
    heading = random.uniform(0, 360)
    steps = int(duration_hours * 60 / interval_min)

    for i in range(steps):
        # Fishing: random heading changes, SOG 2-4 kn
        heading += random.uniform(-35, 35)
        sog = random.uniform(2.0, 4.5)
        cog = heading + random.uniform(-5, 5)
        positions.append({
            "lat": lat, "lon": lon,
            "sog": sog, "cog": cog, "heading": heading,
            "minutes_offset": i * interval_min,
        })
        lat, lon = _advance_position(lat, lon, heading, sog, interval_min)

    return positions


def generate_loitering_track(
    center_lat: float,
    center_lon: float,
    duration_hours: float,
    interval_min: int = 5,
) -> list[dict]:
    """Generate loitering behavior — slow, circular drift."""
    positions = []
    lat, lon = center_lat, center_lon
    heading = random.uniform(0, 360)
    steps = int(duration_hours * 60 / interval_min)

    for i in range(steps):
        heading += random.uniform(-60, 60)
        sog = random.uniform(0.3, 1.8)
        cog = heading + random.uniform(-10, 10)
        positions.append({
            "lat": lat, "lon": lon,
            "sog": sog, "cog": cog, "heading": heading,
            "minutes_offset": i * interval_min,
        })
        lat, lon = _advance_position(lat, lon, heading, sog, interval_min)

    return positions


def generate_anchored_track(
    lat: float,
    lon: float,
    duration_hours: float,
    interval_min: int = 5,
) -> list[dict]:
    """Generate anchored behavior — essentially stationary."""
    positions = []
    steps = int(duration_hours * 60 / interval_min)

    for i in range(steps):
        positions.append({
            "lat": lat + random.uniform(-0.0002, 0.0002),
            "lon": lon + random.uniform(-0.0002, 0.0002),
            "sog": random.uniform(0.0, 0.4),
            "cog": random.uniform(0, 360),
            "heading": random.uniform(0, 360),
            "minutes_offset": i * interval_min,
        })

    return positions


def generate_rendezvous_track(
    meet_lat: float,
    meet_lon: float,
    duration_hours: float,
    interval_min: int = 5,
    offset_nm: float = 0.05,
) -> list[dict]:
    """Generate rendezvous behavior — two vessels hovering close together.

    Returns positions for ONE vessel. Call twice with different offsets for pair.
    """
    positions = []
    steps = int(duration_hours * 60 / interval_min)
    base_lat = meet_lat + (offset_nm / 60.0)
    base_lon = meet_lon + (offset_nm / 60.0)

    for i in range(steps):
        positions.append({
            "lat": base_lat + random.uniform(-0.0004, 0.0004),
            "lon": base_lon + random.uniform(-0.0004, 0.0004),
            "sog": random.uniform(0.1, 1.5),
            "cog": random.uniform(0, 360),
            "heading": random.uniform(0, 360),
            "minutes_offset": i * interval_min,
        })

    return positions


def track_to_observations(
    track: list[dict],
    base_time: datetime,
    mmsi: int,
    vessel_name: str,
    ship_type: int,
    imo: int | None = None,
    call_sign: str | None = None,
    destination: str = "",
    nav_status: int = 0,
    draught: float | None = None,
) -> list[VesselObservation]:
    """Convert a track (list of position dicts) to VesselObservation records."""
    obs = []
    for i, pos in enumerate(track):
        ts = base_time + timedelta(minutes=pos["minutes_offset"])
        obs.append(_make_vessel_obs(
            mmsi=mmsi, ts=ts,
            lat=pos["lat"], lon=pos["lon"],
            sog=pos["sog"], cog=pos["cog"],
            heading=int(pos["heading"]),
            vessel_name=vessel_name,
            ship_type=ship_type,
            imo=imo,
            call_sign=call_sign,
            destination=destination,
            nav_status=nav_status,
            draught=draught,
            idx=i,
        ))
    return obs


# ---------------------------------------------------------------------------
# Scenario builders
# ---------------------------------------------------------------------------

def scenario_1_iuu_fishing() -> list[VesselObservation]:
    """IUU Fishing Suspect — Panama-flagged vessel fishing in MPA with AIS gap.

    MMSI 352001234 (Panama, IUU=0.68)
    - 0-24h: transit toward Mediterranean MPA
    - 24-42h: 18h AIS gap (dark period)
    - 42-60h: fishing inside MPA zone (SOG 2-4, high COG variance)
    - 60-72h: loitering inside MPA
    """
    mmsi = 352001234
    base_time = NOW - timedelta(hours=72)
    all_positions: list[dict] = []

    # Phase 1: Transit (0-24h) heading toward MPA at 36.5N, 2.5W
    transit = generate_transit_track(
        start_lat=37.5, start_lon=-1.0, heading=230, speed_kn=10.0,
        duration_hours=24, interval_min=5,
    )
    all_positions.extend(transit)

    # Phase 2: 18h AIS gap (24-42h) — no positions
    gap_offset = 24 * 60  # minutes

    # Phase 3: Fishing inside MPA (42-60h)
    fishing = generate_fishing_track(
        start_lat=36.5, start_lon=-2.5,
        duration_hours=18, interval_min=5,
    )
    for p in fishing:
        p["minutes_offset"] += gap_offset + 18 * 60  # after gap
    all_positions.extend(fishing)

    # Phase 4: Loitering in MPA (60-72h)
    loiter = generate_loitering_track(
        center_lat=36.45, center_lon=-2.55,
        duration_hours=12, interval_min=5,
    )
    for p in loiter:
        p["minutes_offset"] += gap_offset + 36 * 60  # after fishing
    all_positions.extend(loiter)

    return track_to_observations(
        all_positions, base_time,
        mmsi=mmsi,
        vessel_name="OCEAN HUNTER",
        ship_type=30,  # Fishing
        imo=None,  # Missing IMO — identity risk
        call_sign="3FPA7",
        destination="CASABLANCA",
        nav_status=7,  # Engaged in fishing
        draught=4.5,
    )


def scenario_2_transshipment() -> tuple[list[VesselObservation], list[VesselObservation]]:
    """Open-ocean transshipment — two vessels rendezvous mid-Atlantic.

    Vessel A: MMSI 514012345 (Cambodia, IUU=0.80) — reefer/fishing
    Vessel B: MMSI 636091234 (Liberia, IUU=0.70) — tanker
    - 0-20h: both transit toward meeting point
    - 20-24h: rendezvous (SOG <2kn, <0.08nm apart)
    - 24-48h: diverge in opposite directions
    """
    mmsi_a = 514012345
    mmsi_b = 636091234
    meet_lat, meet_lon = 15.5, -35.0
    base_time = NOW - timedelta(hours=48)

    # --- Vessel A ---
    track_a: list[dict] = []

    # A transit to meeting (0-20h)
    transit_a = generate_transit_track(
        start_lat=17.0, start_lon=-33.0, heading=210, speed_kn=11.0,
        duration_hours=20, interval_min=5,
    )
    track_a.extend(transit_a)

    # A rendezvous (20-24h)
    rdv_a = generate_rendezvous_track(
        meet_lat=meet_lat, meet_lon=meet_lon,
        duration_hours=4, interval_min=5, offset_nm=0.03,
    )
    for p in rdv_a:
        p["minutes_offset"] += 20 * 60
    track_a.extend(rdv_a)

    # A depart (24-48h)
    depart_a = generate_transit_track(
        start_lat=meet_lat + 0.01, start_lon=meet_lon - 0.01,
        heading=140, speed_kn=10.0,
        duration_hours=24, interval_min=5,
    )
    for p in depart_a:
        p["minutes_offset"] += 24 * 60
    track_a.extend(depart_a)

    obs_a = track_to_observations(
        track_a, base_time,
        mmsi=mmsi_a,
        vessel_name="KHMER REEFER",
        ship_type=30,  # Fishing
        imo=None,
        call_sign="XU2A9",
        destination="DAKAR",
        draught=5.2,
    )

    # --- Vessel B ---
    track_b: list[dict] = []

    # B transit to meeting (0-20h) from opposite direction
    transit_b = generate_transit_track(
        start_lat=14.0, start_lon=-37.0, heading=50, speed_kn=12.0,
        duration_hours=20, interval_min=5,
    )
    track_b.extend(transit_b)

    # B rendezvous (20-24h)
    rdv_b = generate_rendezvous_track(
        meet_lat=meet_lat, meet_lon=meet_lon,
        duration_hours=4, interval_min=5, offset_nm=-0.03,
    )
    for p in rdv_b:
        p["minutes_offset"] += 20 * 60
    track_b.extend(rdv_b)

    # B depart (24-48h)
    depart_b = generate_transit_track(
        start_lat=meet_lat - 0.01, start_lon=meet_lon + 0.01,
        heading=310, speed_kn=11.0,
        duration_hours=24, interval_min=5,
    )
    for p in depart_b:
        p["minutes_offset"] += 24 * 60
    track_b.extend(depart_b)

    obs_b = track_to_observations(
        track_b, base_time,
        mmsi=mmsi_b,
        vessel_name="DARK HORIZON",
        ship_type=89,  # Tanker - No info
        imo=None,  # Missing
        call_sign=None,
        destination="UNKNOWN",
        draught=12.0,
    )

    return obs_a, obs_b


def scenario_3_legitimate_cargo() -> list[VesselObservation]:
    """Legitimate cargo vessel — clean transit, Lisbon to Rotterdam.

    MMSI 255123456 (Portugal, IUU=0.27)
    - Full 72h continuous track, no gaps
    - Steady 14-16 kn, low COG variance
    - Valid IMO, proper identity
    """
    mmsi = 255123456
    base_time = NOW - timedelta(hours=72)

    track = generate_transit_track(
        start_lat=38.7, start_lon=-9.1,
        heading=10, speed_kn=15.0,
        duration_hours=72, interval_min=5,
    )

    return track_to_observations(
        track, base_time,
        mmsi=mmsi,
        vessel_name="LISBON EXPRESS",
        ship_type=70,  # Cargo
        imo=9876543,
        call_sign="CQPN",
        destination="ROTTERDAM",
        nav_status=0,  # Under way using engine
        draught=11.5,
    )


def scenario_4_ais_manipulation() -> list[VesselObservation]:
    """AIS manipulation + restricted zone intrusion — Persian Gulf.

    MMSI 371234567 (Panama, IUU=0.68)
    - 0-18h: normal transit
    - 18-42h: 24h AIS gap
    - 42-48h: erratic positions (jump 200nm), inside restricted zone
    - 48-60h: slow transit out of zone
    """
    mmsi = 371234567
    base_time = NOW - timedelta(hours=60)
    all_positions: list[dict] = []

    # Phase 1: Normal transit (0-18h)
    transit = generate_transit_track(
        start_lat=24.5, start_lon=52.0, heading=310, speed_kn=12.0,
        duration_hours=18, interval_min=5,
    )
    all_positions.extend(transit)

    # Phase 2: 24h gap (18-42h) — no positions

    # Phase 3: Erratic positions inside restricted zone (42-48h)
    # Vessel "appears" far from where it should be
    erratic_start = 42 * 60
    for i in range(72):  # 6h at 5-min intervals
        lat = 26.2 + random.uniform(-0.1, 0.1)
        lon = 50.5 + random.uniform(-0.1, 0.1)
        all_positions.append({
            "lat": lat, "lon": lon,
            "sog": random.uniform(0.5, 3.0),
            "cog": random.uniform(0, 360),
            "heading": random.uniform(0, 360),
            "minutes_offset": erratic_start + i * 5,
        })

    # Phase 4: Slow exit from zone (48-60h)
    exit_track = generate_transit_track(
        start_lat=26.3, start_lon=50.3, heading=180, speed_kn=8.0,
        duration_hours=12, interval_min=5,
    )
    for p in exit_track:
        p["minutes_offset"] += 48 * 60
    all_positions.extend(exit_track)

    return track_to_observations(
        all_positions, base_time,
        mmsi=mmsi,
        vessel_name="UNKNOWN",  # Suspicious name — identity risk
        ship_type=89,  # Tanker - No additional info
        imo=None,
        call_sign=None,
        destination="",
        draught=14.0,
    )


def scenario_5_fishing_fleet() -> tuple[
    list[VesselObservation],
    list[VesselObservation],
    list[VesselObservation],
]:
    """Fishing fleet in Norwegian Sea — mixed compliance.

    Vessel A: MMSI 240567890 (Netherlands, IUU=0.10) — clean
    Vessel B: MMSI 613004567 (Cameroon, IUU=0.82) — 8h gap, enters EEZ
    Vessel C: MMSI 257678901 (Norway, IUU=0.12) — clean
    """
    base_time = NOW - timedelta(hours=72)

    # --- Vessel A (clean) ---
    track_a = generate_fishing_track(
        start_lat=67.5, start_lon=12.5,
        duration_hours=72, interval_min=5,
    )
    obs_a = track_to_observations(
        track_a, base_time,
        mmsi=240567890,
        vessel_name="NOORDZEE",
        ship_type=30,
        imo=8712345,
        call_sign="PDFT",
        destination="TROMSO",
        nav_status=7,
        draught=4.0,
    )

    # --- Vessel B (dirty — gap + EEZ entry) ---
    track_b_parts: list[dict] = []

    # Fishing 0-30h
    fish_b1 = generate_fishing_track(
        start_lat=67.3, start_lon=11.8,
        duration_hours=30, interval_min=5,
    )
    track_b_parts.extend(fish_b1)

    # 8h gap (30-38h) — no positions

    # Fishing inside EEZ 38-72h
    fish_b2 = generate_fishing_track(
        start_lat=67.6, start_lon=13.0,
        duration_hours=34, interval_min=5,
    )
    for p in fish_b2:
        p["minutes_offset"] += 38 * 60
    track_b_parts.extend(fish_b2)

    obs_b = track_to_observations(
        track_b_parts, base_time,
        mmsi=613004567,
        vessel_name="AFRIQUE PECHE",
        ship_type=30,
        imo=None,  # Missing
        call_sign=None,
        destination="DOUALA",
        nav_status=7,
        draught=3.8,
    )

    # --- Vessel C (clean) ---
    track_c = generate_fishing_track(
        start_lat=67.7, start_lon=13.5,
        duration_hours=72, interval_min=5,
    )
    obs_c = track_to_observations(
        track_c, base_time,
        mmsi=257678901,
        vessel_name="HAVBRIS",
        ship_type=30,
        imo=9234567,
        call_sign="LNBR",
        destination="BODO",
        nav_status=7,
        draught=3.5,
    )

    return obs_a, obs_b, obs_c


def scenario_6_port_anchorage() -> tuple[
    list[VesselObservation], list[VesselObservation]
]:
    """Two vessels anchored near Rotterdam — low risk baseline.

    Vessel A: MMSI 232345678 (UK) — cargo at anchor
    Vessel B: MMSI 246789012 (Netherlands) — tanker at anchor
    """
    base_time = NOW - timedelta(hours=48)

    # Vessel A: anchored near Rotterdam
    track_a = generate_anchored_track(
        lat=51.95, lon=4.05,
        duration_hours=48, interval_min=10,
    )
    obs_a = track_to_observations(
        track_a, base_time,
        mmsi=232345678,
        vessel_name="THAMES CARRIER",
        ship_type=70,
        imo=9345678,
        call_sign="MOPQ",
        destination="ROTTERDAM",
        nav_status=1,  # At anchor
        draught=9.0,
    )

    # Vessel B: anchored nearby
    track_b = generate_anchored_track(
        lat=51.96, lon=4.07,
        duration_hours=48, interval_min=10,
    )
    obs_b = track_to_observations(
        track_b, base_time,
        mmsi=246789012,
        vessel_name="HOLLAND SPIRIT",
        ship_type=80,
        imo=9456789,
        call_sign="PBSP",
        destination="EUROPOORT",
        nav_status=1,
        draught=10.5,
    )

    return obs_a, obs_b


# ---------------------------------------------------------------------------
# Geofence data
# ---------------------------------------------------------------------------

def create_geofence_zones() -> list[GeofenceZone]:
    """Create 3 geofence monitoring zones."""
    zones = []

    # Zone 1: Mediterranean MPA (around scenario 1 fishing area)
    zones.append(GeofenceZone(
        id=uuid.UUID("a0000001-0000-4000-8000-000000000001"),
        name="Alboran Sea Marine Protected Area",
        description="Protected marine area in the western Mediterranean, "
                    "critical habitat for cetaceans and seabirds.",
        zone_type="polygon",
        geometry_data={
            "coordinates": [[
                [-2.8, 36.3], [-2.2, 36.3], [-2.2, 36.7],
                [-2.8, 36.7], [-2.8, 36.3],
            ]]
        },
        is_active=True,
        category="mpa",
        metadata_={"seed": "demo", "iucn_category": "II", "area_km2": 1850},
    ))

    # Zone 2: Persian Gulf Restricted (around scenario 4)
    zones.append(GeofenceZone(
        id=uuid.UUID("a0000002-0000-4000-8000-000000000002"),
        name="Persian Gulf Naval Exclusion Zone",
        description="Restricted naval zone — unauthorized entry prohibited.",
        zone_type="polygon",
        geometry_data={
            "coordinates": [[
                [50.2, 25.9], [50.8, 25.9], [50.8, 26.5],
                [50.2, 26.5], [50.2, 25.9],
            ]]
        },
        is_active=True,
        category="restricted",
        metadata_={"seed": "demo", "authority": "CENTCOM"},
    ))

    # Zone 3: Norwegian EEZ Fishing Grounds
    zones.append(GeofenceZone(
        id=uuid.UUID("a0000003-0000-4000-8000-000000000003"),
        name="Norwegian EEZ — Lofoten Fishing Zone",
        description="Norwegian exclusive economic zone. Foreign fishing vessels "
                    "require permits.",
        zone_type="polygon",
        geometry_data={
            "coordinates": [[
                [12.0, 67.0], [14.0, 67.0], [14.0, 68.0],
                [12.0, 68.0], [12.0, 67.0],
            ]]
        },
        is_active=True,
        category="eez",
        metadata_={"seed": "demo", "country": "NO", "fishery": "cod_haddock"},
    ))

    return zones


def create_geofence_rules(zones: list[GeofenceZone]) -> list[GeofenceRule]:
    """Create monitoring rules for each zone."""
    rules = []
    zone_ids = {z.category: z.id for z in zones}

    # MPA rules
    mpa_id = zone_ids["mpa"]
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000001-0000-4000-8000-000000000001"),
        zone_id=mpa_id, rule_type="entry", severity="critical",
        parameters=None, is_active=True,
    ))
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000002-0000-4000-8000-000000000002"),
        zone_id=mpa_id, rule_type="loiter", severity="alert",
        parameters={"threshold_minutes": 30}, is_active=True,
    ))
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000003-0000-4000-8000-000000000003"),
        zone_id=mpa_id, rule_type="speed", severity="warning",
        parameters={"max_speed_kn": 5.0}, is_active=True,
    ))

    # Restricted zone rules
    restricted_id = zone_ids["restricted"]
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000004-0000-4000-8000-000000000004"),
        zone_id=restricted_id, rule_type="entry", severity="critical",
        parameters=None, is_active=True,
    ))
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000005-0000-4000-8000-000000000005"),
        zone_id=restricted_id, rule_type="ais_off", severity="critical",
        parameters={"gap_hours": 6}, is_active=True,
    ))

    # EEZ rules
    eez_id = zone_ids["eez"]
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000006-0000-4000-8000-000000000006"),
        zone_id=eez_id, rule_type="entry", severity="alert",
        parameters=None,
        vessel_filter={"ship_types": [30]},  # Fishing vessels only
        is_active=True,
    ))
    rules.append(GeofenceRule(
        id=uuid.UUID("b0000007-0000-4000-8000-000000000007"),
        zone_id=eez_id, rule_type="ais_off", severity="alert",
        parameters={"gap_hours": 4}, is_active=True,
    ))

    return rules


def create_geofence_alerts(
    zones: list[GeofenceZone], rules: list[GeofenceRule]
) -> list[GeofenceAlert]:
    """Pre-generate alerts for scenario vessels."""
    alerts = []

    # Helper to find rule by zone category + type
    def find_rule(category: str, rule_type: str) -> GeofenceRule | None:
        zone = next((z for z in zones if z.category == category), None)
        if not zone:
            return None
        return next(
            (r for r in rules if r.zone_id == zone.id and r.rule_type == rule_type),
            None,
        )

    # --- Scenario 1: IUU vessel in MPA ---
    mpa_zone = next(z for z in zones if z.category == "mpa")
    entry_rule = find_rule("mpa", "entry")
    loiter_rule = find_rule("mpa", "loiter")

    if entry_rule:
        alerts.append(GeofenceAlert(
            id=uuid.uuid4(),
            zone_id=mpa_zone.id,
            rule_id=entry_rule.id,
            mmsi=352001234,
            rule_type="entry",
            severity="critical",
            triggered_at=NOW - timedelta(hours=30),
            lat=36.5, lon=-2.5,
            details={
                "seed": "demo",
                "message": "Fishing vessel entered Alboran Sea MPA",
                "vessel_name": "OCEAN HUNTER",
            },
        ))

    if loiter_rule:
        alerts.append(GeofenceAlert(
            id=uuid.uuid4(),
            zone_id=mpa_zone.id,
            rule_id=loiter_rule.id,
            mmsi=352001234,
            rule_type="loiter",
            severity="alert",
            triggered_at=NOW - timedelta(hours=28),
            lat=36.48, lon=-2.52,
            details={
                "seed": "demo",
                "message": "Vessel loitering >30 min in MPA",
                "duration_minutes": 185,
            },
        ))

    # --- Scenario 4: Manipulated vessel in restricted zone ---
    restricted_zone = next(z for z in zones if z.category == "restricted")
    entry_rule_r = find_rule("restricted", "entry")
    ais_rule_r = find_rule("restricted", "ais_off")

    if entry_rule_r:
        alerts.append(GeofenceAlert(
            id=uuid.uuid4(),
            zone_id=restricted_zone.id,
            rule_id=entry_rule_r.id,
            mmsi=371234567,
            rule_type="entry",
            severity="critical",
            triggered_at=NOW - timedelta(hours=18),
            lat=26.2, lon=50.5,
            details={
                "seed": "demo",
                "message": "Unauthorized vessel entered naval exclusion zone",
                "vessel_name": "UNKNOWN",
            },
        ))

    if ais_rule_r:
        alerts.append(GeofenceAlert(
            id=uuid.uuid4(),
            zone_id=restricted_zone.id,
            rule_id=ais_rule_r.id,
            mmsi=371234567,
            rule_type="ais_off",
            severity="critical",
            triggered_at=NOW - timedelta(hours=42),
            lat=25.8, lon=51.5,
            details={
                "seed": "demo",
                "message": "24h AIS gap detected near restricted zone",
                "gap_hours": 24,
            },
        ))

    # --- Scenario 5: Cameroon vessel in Norwegian EEZ ---
    eez_zone = next(z for z in zones if z.category == "eez")
    entry_rule_e = find_rule("eez", "entry")
    ais_rule_e = find_rule("eez", "ais_off")

    if entry_rule_e:
        alerts.append(GeofenceAlert(
            id=uuid.uuid4(),
            zone_id=eez_zone.id,
            rule_id=entry_rule_e.id,
            mmsi=613004567,
            rule_type="entry",
            severity="alert",
            triggered_at=NOW - timedelta(hours=34),
            lat=67.6, lon=13.0,
            details={
                "seed": "demo",
                "message": "Foreign fishing vessel entered Norwegian EEZ",
                "vessel_name": "AFRIQUE PECHE",
                "flag": "CM",
            },
        ))

    if ais_rule_e:
        alerts.append(GeofenceAlert(
            id=uuid.uuid4(),
            zone_id=eez_zone.id,
            rule_id=ais_rule_e.id,
            mmsi=613004567,
            rule_type="ais_off",
            severity="alert",
            triggered_at=NOW - timedelta(hours=38),
            lat=67.4, lon=12.5,
            details={
                "seed": "demo",
                "message": "8h AIS gap detected in Norwegian EEZ",
                "gap_hours": 8,
            },
        ))

    return alerts


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

async def ensure_geofence_tables() -> None:
    """Create geofence tables if they don't exist (fallback if migration not run)."""
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    GeofenceZone.__table__,
                    GeofenceRule.__table__,
                    GeofenceAlert.__table__,
                ],
            )
        )


async def clear_demo_data() -> None:
    """Remove all previously seeded demo data."""
    async with async_session_factory() as session:
        # Clear in dependency order
        await session.execute(
            text("DELETE FROM geofence_alerts WHERE details->>'seed' = 'demo'")
        )
        await session.execute(
            text("DELETE FROM geofence_rules WHERE zone_id IN "
                 "(SELECT id FROM geofence_zones WHERE metadata->>'seed' = 'demo')")
        )
        await session.execute(
            text("DELETE FROM geofence_zones WHERE metadata->>'seed' = 'demo'")
        )
        await session.execute(
            delete(Observation).where(Observation.source_name == "DEMO_SEED")
        )
        await session.commit()
    print("  Cleared previous demo data")


async def seed_demo() -> None:
    """Seed comprehensive demo data for all risk engines."""
    print("=" * 60)
    print("  OKEANUS DEMO SEED")
    print("=" * 60)

    # 1. Ensure geofence tables exist
    print("\n[1/5] Ensuring geofence tables exist...")
    await ensure_geofence_tables()
    print("  OK")

    # 2. Clear existing demo data
    print("\n[2/5] Clearing previous demo data...")
    await clear_demo_data()

    # 3. Generate all vessel observations
    print("\n[3/5] Generating vessel scenarios...")
    all_obs: list[VesselObservation] = []

    # Scenario 1: IUU Fishing Suspect
    s1 = scenario_1_iuu_fishing()
    all_obs.extend(s1)
    print(f"  Scenario 1 — IUU Fishing (352001234):       {len(s1):>5} positions")

    # Scenario 2: Transshipment
    s2a, s2b = scenario_2_transshipment()
    all_obs.extend(s2a)
    all_obs.extend(s2b)
    print(f"  Scenario 2 — Transshipment (514012345):      {len(s2a):>5} positions")
    print(f"               Transshipment (636091234):      {len(s2b):>5} positions")

    # Scenario 3: Legitimate Cargo
    s3 = scenario_3_legitimate_cargo()
    all_obs.extend(s3)
    print(f"  Scenario 3 — Legitimate Cargo (255123456):   {len(s3):>5} positions")

    # Scenario 4: AIS Manipulation
    s4 = scenario_4_ais_manipulation()
    all_obs.extend(s4)
    print(f"  Scenario 4 — AIS Manipulation (371234567):   {len(s4):>5} positions")

    # Scenario 5: Fishing Fleet
    s5a, s5b, s5c = scenario_5_fishing_fleet()
    all_obs.extend(s5a)
    all_obs.extend(s5b)
    all_obs.extend(s5c)
    print(f"  Scenario 5 — Fleet Clean NL (240567890):     {len(s5a):>5} positions")
    print(f"               Fleet Dirty CM (613004567):     {len(s5b):>5} positions")
    print(f"               Fleet Clean NO (257678901):     {len(s5c):>5} positions")

    # Scenario 6: Port Anchorage
    s6a, s6b = scenario_6_port_anchorage()
    all_obs.extend(s6a)
    all_obs.extend(s6b)
    print(f"  Scenario 6 — Anchored UK (232345678):        {len(s6a):>5} positions")
    print(f"               Anchored NL (246789012):        {len(s6b):>5} positions")

    print(f"\n  TOTAL: {len(all_obs)} vessel observations")

    # 4. Insert observations in batches
    print("\n[4/5] Inserting observations...")
    batch_size = 500
    for i in range(0, len(all_obs), batch_size):
        batch = all_obs[i : i + batch_size]
        async with async_session_factory() as session:
            session.add_all(batch)
            await session.commit()
        print(f"  Batch {i // batch_size + 1}: {len(batch)} records")
    print("  OK")

    # 5. Create geofence data
    print("\n[5/5] Creating geofence zones, rules, and alerts...")
    zones = create_geofence_zones()
    rules = create_geofence_rules(zones)
    alerts = create_geofence_alerts(zones, rules)

    async with async_session_factory() as session:
        session.add_all(zones)
        session.add_all(rules)
        session.add_all(alerts)
        await session.commit()

    print(f"  {len(zones)} zones created")
    print(f"  {len(rules)} rules created")
    print(f"  {len(alerts)} alerts created")

    # Summary
    print("\n" + "=" * 60)
    print("  SEED COMPLETE")
    print("=" * 60)
    print(f"\n  {len(all_obs)} vessel observations across 10 vessels")
    print(f"  {len(zones)} geofence zones with {len(rules)} rules")
    print(f"  {len(alerts)} pre-generated geofence alerts")
    print("\n  Expected risk scores:")
    print("    352001234 (IUU Fisher)     — CRITICAL (~75+)")
    print("    514012345 (Cambodia Reefer) — HIGH (~65+)")
    print("    636091234 (Liberia Tanker)  — HIGH (~65+)")
    print("    255123456 (Lisbon Express)  — LOW (~15-25)")
    print("    371234567 (AIS Manipulator) — CRITICAL (~80+)")
    print("    240567890 (NL Fisher)       — LOW (~20)")
    print("    613004567 (CM Fisher)       — HIGH (~65)")
    print("    257678901 (NO Fisher)       — LOW (~18)")
    print("    232345678 (UK Cargo)        — LOW (~10)")
    print("    246789012 (NL Tanker)       — LOW (~15)")
    print("\n  Verify with:")
    print("    curl http://localhost:8000/ml/risk/352001234")
    print("    curl http://localhost:8000/ml/risk/fleet/summary")
    print("    curl http://localhost:8000/geofence/alerts/summary")
    print("    curl http://localhost:8000/ml/behavioral/trajectory/352001234")
    print("    curl http://localhost:8000/ml/behavioral/encounters/514012345")


if __name__ == "__main__":
    asyncio.run(seed_demo())
