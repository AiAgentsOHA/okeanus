"""Seed the PostGIS database with sample observations across all 5 domains.

Usage:
    DATABASE_URL="postgresql+asyncpg://okeanus:okeanus@localhost:5432/okeanus" \
        python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon

from okeanus.db.postgres import async_session_factory
from okeanus.schema.base import Observation

random.seed(42)

# ---------------------------------------------------------------------------
# Sample data generators
# ---------------------------------------------------------------------------

NOW = datetime.now(UTC)

# Mediterranean / NE Atlantic bounding box for variety
REGIONS = {
    "med_west": {"lon": (-5.0, 3.0), "lat": (35.0, 43.0)},
    "med_east": {"lon": (15.0, 30.0), "lat": (30.0, 40.0)},
    "north_sea": {"lon": (-3.0, 8.0), "lat": (51.0, 58.0)},
    "atlantic": {"lon": (-20.0, -5.0), "lat": (35.0, 50.0)},
    "baltic": {"lon": (10.0, 25.0), "lat": (54.0, 60.0)},
}


def rand_point(region: str = "med_west") -> Point:
    r = REGIONS[region]
    lon = random.uniform(*r["lon"])
    lat = random.uniform(*r["lat"])
    return Point(lon, lat)


def rand_time(days_back: int = 30) -> datetime:
    return NOW - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


def make_observation(**kwargs) -> Observation:
    geom = kwargs.pop("geom")
    return Observation(
        id=uuid.uuid4(),
        geometry=from_shape(geom, srid=4326),
        created_at=NOW,
        updated_at=NOW,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Physical observations (SST, salinity, currents)
# ---------------------------------------------------------------------------

def physical_observations(n: int = 40) -> list[Observation]:
    obs = []
    sources = [
        ("cmems", "Copernicus Marine"),
        ("argo", "Argo Float Network"),
        ("edito", "EU Digital Twin Ocean"),
    ]
    params = ["sst", "salinity", "sea_level", "current_speed", "wave_height"]
    regions = ["med_west", "med_east", "north_sea", "atlantic", "baltic"]

    for i in range(n):
        src_id, src_name = sources[i % len(sources)]
        param = params[i % len(params)]
        region = regions[i % len(regions)]

        value = {
            "sst": round(random.uniform(8.0, 28.0), 2),
            "salinity": round(random.uniform(30.0, 39.0), 2),
            "sea_level": round(random.uniform(-0.5, 0.8), 3),
            "current_speed": round(random.uniform(0.01, 1.5), 3),
            "wave_height": round(random.uniform(0.2, 5.0), 2),
        }[param]

        obs.append(make_observation(
            obs_type="physical",
            timestamp=rand_time(),
            geom=rand_point(region),
            source_id=f"{src_id}-{region}-{i:04d}",
            source_name=src_name,
            quality_score=round(random.uniform(0.7, 1.0), 2),
            payload={
                "parameter": param,
                "value": value,
                "unit": {"sst": "°C", "salinity": "PSU", "sea_level": "m",
                         "current_speed": "m/s", "wave_height": "m"}[param],
                "depth_m": round(random.uniform(0, 200), 1) if param != "wave_height" else 0,
            },
        ))
    return obs


# ---------------------------------------------------------------------------
# Vessel observations (AIS positions)
# ---------------------------------------------------------------------------

VESSEL_NAMES = [
    "EMMA MAERSK", "MSC OSCAR", "OASIS OF THE SEAS", "AKADEMIK SHOKALSKIY",
    "POLARSTERN", "CELTIC EXPLORER", "JOIDES RESOLUTION", "MARIA S. MERIAN",
    "JAMES COOK", "PELAGIA", "RV BELGICA", "ATLANTIC GUARDIAN",
]


def vessel_observations(n: int = 30) -> list[Observation]:
    obs = []
    for i in range(n):
        mmsi = 200000000 + i * 1000 + random.randint(0, 999)
        name = VESSEL_NAMES[i % len(VESSEL_NAMES)]
        region = list(REGIONS.keys())[i % len(REGIONS)]

        obs.append(make_observation(
            obs_type="vessel",
            timestamp=rand_time(days_back=7),
            geom=rand_point(region),
            source_id=f"ais-{mmsi}-{i:04d}",
            source_name="AISStream",
            mmsi=mmsi,
            quality_score=round(random.uniform(0.85, 1.0), 2),
            payload={
                "vessel_name": name,
                "vessel_type": random.choice([
                    "cargo", "tanker", "fishing", "research", "passenger",
                ]),
                "speed_knots": round(random.uniform(0, 22), 1),
                "heading_deg": round(random.uniform(0, 360), 1),
                "draught_m": round(random.uniform(3, 16), 1),
                "flag": random.choice(["NL", "DE", "NO", "FR", "GB", "PA", "LR"]),
            },
        ))
    return obs


# ---------------------------------------------------------------------------
# Acoustic observations (hydrophone detections)
# ---------------------------------------------------------------------------

def acoustic_observations(n: int = 20) -> list[Observation]:
    obs = []
    species_sounds = [
        ("blue_whale", 15.0, 25.0), ("fin_whale", 18.0, 28.0),
        ("sperm_whale", 5000.0, 25000.0), ("dolphin", 2000.0, 150000.0),
        ("ship_noise", 50.0, 1000.0), ("seismic_survey", 10.0, 200.0),
    ]
    for i in range(n):
        species, freq_low, freq_high = species_sounds[i % len(species_sounds)]
        region = list(REGIONS.keys())[i % len(REGIONS)]

        obs.append(make_observation(
            obs_type="acoustic",
            timestamp=rand_time(days_back=14),
            geom=rand_point(region),
            source_id=f"hydro-{region}-{i:04d}",
            source_name="ONC Hydrophones",
            quality_score=round(random.uniform(0.5, 0.95), 2),
            payload={
                "sound_type": species,
                "freq_min_hz": freq_low,
                "freq_max_hz": freq_high,
                "duration_sec": round(random.uniform(0.5, 30.0), 2),
                "spl_db": round(random.uniform(80, 180), 1),
                "hydrophone_depth_m": round(random.uniform(50, 2000), 0),
            },
        ))
    return obs


# ---------------------------------------------------------------------------
# Biological observations (species sightings)
# ---------------------------------------------------------------------------

SPECIES = [
    ("Balaenoptera musculus", 137090, "blue whale"),
    ("Tursiops truncatus", 137111, "bottlenose dolphin"),
    ("Caretta caretta", 137205, "loggerhead turtle"),
    ("Posidonia oceanica", 145793, "Neptune grass"),
    ("Sardina pilchardus", 126421, "sardine"),
    ("Thunnus thynnus", 127029, "Atlantic bluefin tuna"),
    ("Halichoerus grypus", 137080, "grey seal"),
    ("Carcharodon carcharias", 105838, "great white shark"),
]


def biological_observations(n: int = 25) -> list[Observation]:
    obs = []
    for i in range(n):
        sci_name, aphia, common = SPECIES[i % len(SPECIES)]
        region = list(REGIONS.keys())[i % len(REGIONS)]

        obs.append(make_observation(
            obs_type="biological",
            timestamp=rand_time(days_back=60),
            geom=rand_point(region),
            source_id=f"obis-{aphia}-{i:04d}",
            source_name="OBIS",
            aphia_id=aphia,
            quality_score=round(random.uniform(0.6, 1.0), 2),
            payload={
                "scientific_name": sci_name,
                "common_name": common,
                "count": random.randint(1, 50),
                "observation_method": random.choice([
                    "visual", "net_tow", "acoustic", "camera_trap",
                ]),
                "depth_m": round(random.uniform(0, 300), 1),
            },
        ))
    return obs


# ---------------------------------------------------------------------------
# Satellite observations (footprints as polygons)
# ---------------------------------------------------------------------------

def satellite_observations(n: int = 15) -> list[Observation]:
    obs = []
    missions = [
        ("sentinel-2", "Sentinel-2 MSI"), ("sentinel-3", "Sentinel-3 OLCI"),
        ("landsat-9", "Landsat 9 OLI"), ("modis-aqua", "MODIS Aqua"),
    ]
    for i in range(n):
        mission_id, mission_name = missions[i % len(missions)]
        region = list(REGIONS.keys())[i % len(REGIONS)]

        # Create a small rectangular footprint (~1° × 1°)
        center = rand_point(region)
        cx, cy = center.x, center.y
        half = 0.5
        footprint = Polygon([
            (cx - half, cy - half), (cx + half, cy - half),
            (cx + half, cy + half), (cx - half, cy + half),
            (cx - half, cy - half),
        ])

        obs.append(make_observation(
            obs_type="satellite",
            timestamp=rand_time(days_back=10),
            geom=footprint,
            source_id=f"{mission_id}-{i:04d}",
            source_name=mission_name,
            quality_score=round(random.uniform(0.3, 1.0), 2),
            payload={
                "mission": mission_id,
                "cloud_cover_pct": round(random.uniform(0, 80), 1),
                "resolution_m": {"sentinel-2": 10, "sentinel-3": 300,
                                 "landsat-9": 30, "modis-aqua": 1000}[mission_id],
                "bands": ["B1", "B2", "B3", "B4"],
                "orbit_direction": random.choice(["ascending", "descending"]),
            },
        ))
    return obs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def seed():
    all_obs = (
        physical_observations(40)
        + vessel_observations(30)
        + acoustic_observations(20)
        + biological_observations(25)
        + satellite_observations(15)
    )
    random.shuffle(all_obs)

    async with async_session_factory() as session:
        session.add_all(all_obs)
        await session.commit()

    print(f"Seeded {len(all_obs)} observations:")
    print("  physical:   40")
    print("  vessel:     30")
    print("  acoustic:   20")
    print("  biological: 25")
    print("  satellite:  15")


if __name__ == "__main__":
    asyncio.run(seed())
