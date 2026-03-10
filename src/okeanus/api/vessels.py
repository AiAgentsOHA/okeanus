"""Vessel position endpoints returning GeoJSON."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from geojson_pydantic import Feature, FeatureCollection, Point

router = APIRouter(prefix="/vessels", tags=["vessels"])


def _mock_vessel(mmsi: int, lon: float, lat: float) -> Feature:
    """Create a mock vessel feature."""
    return Feature(
        type="Feature",
        id=str(uuid.uuid4()),
        geometry=Point(type="Point", coordinates=[lon, lat]),
        properties={
            "mmsi": mmsi,
            "obs_type": "vessel",
            "timestamp": datetime.now(UTC).isoformat(),
            "source_name": "mock-ais",
            "source_id": f"ais-{mmsi}",
            "ship_name": f"VESSEL-{mmsi}",
            "speed_over_ground": 12.5,
            "course_over_ground": 180.0,
        },
    )


# Sample mock vessels for MVP
_MOCK_VESSELS = {
    123456789: (18.4241, -33.9249),
    987654321: (55.2708, -21.1151),
    111222333: (3.7038, 43.4075),
    444555666: (-43.1729, -22.9068),
    777888999: (103.8198, 1.3521),
}


@router.get("", response_model=FeatureCollection)
async def list_vessels(
    mmsi: Annotated[int | None, Query(description="Filter by MMSI number")] = None,
    bbox: Annotated[
        str | None,
        Query(
            description="Bounding box: west,south,east,north",
            pattern=r"^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$",
        ),
    ] = None,
    time_start: Annotated[
        datetime | None,
        Query(description="Start of time range (ISO 8601)"),
    ] = None,
    time_end: Annotated[
        datetime | None,
        Query(description="End of time range (ISO 8601)"),
    ] = None,
) -> FeatureCollection:
    """Query vessel positions by MMSI, bounding box, and time range.

    Returns a GeoJSON FeatureCollection. For MVP, returns mock data.
    """
    features: list[Feature] = []
    for vessel_mmsi, (lon, lat) in _MOCK_VESSELS.items():
        if mmsi and vessel_mmsi != mmsi:
            continue
        if bbox:
            parts = [float(x) for x in bbox.split(",")]
            west, south, east, north = parts[0], parts[1], parts[2], parts[3]
            if not (west <= lon <= east and south <= lat <= north):
                continue
        features.append(_mock_vessel(vessel_mmsi, lon, lat))

    return FeatureCollection(type="FeatureCollection", features=features)


@router.get("/{mmsi}", response_model=Feature)
async def get_vessel(mmsi: int) -> Feature:
    """Get the latest position for a specific vessel by MMSI.

    Returns a single GeoJSON Feature.
    """
    if mmsi not in _MOCK_VESSELS:
        raise HTTPException(status_code=404, detail=f"Vessel with MMSI {mmsi} not found")

    lon, lat = _MOCK_VESSELS[mmsi]
    return _mock_vessel(mmsi, lon, lat)
