"""Marine Regions search and lookup endpoints."""

from __future__ import annotations

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/regions", tags=["regions"])

MARINE_REGIONS_BASE = "https://www.marineregions.org/rest"


@router.get("/search")
async def search_regions(
    name: Annotated[str, Query(min_length=2, description="Region name to search for")],
) -> list[dict]:
    """Search Marine Regions by name.

    Proxies the marineregions.org REST API and returns matching regions.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{MARINE_REGIONS_BASE}/getGazetteerRecordsByName.json/{name}/",
                params={"like": "true", "offset": 0, "count": 20},
            )
            resp.raise_for_status()
            records = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return []
        raise HTTPException(status_code=502, detail="Marine Regions API error")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach Marine Regions API")

    return [
        {
            "mrgid": r.get("MRGID"),
            "name": r.get("preferredGazetteerName"),
            "place_type": r.get("placeType"),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
        }
        for r in records
    ]


@router.get("/{mrgid}")
async def get_region(mrgid: int) -> dict:
    """Get a Marine Region by its MRGID identifier."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{MARINE_REGIONS_BASE}/getGazetteerRecordByMRGID.json/{mrgid}/"
            )
            resp.raise_for_status()
            record = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Region MRGID {mrgid} not found")
        raise HTTPException(status_code=502, detail="Marine Regions API error")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach Marine Regions API")

    return {
        "mrgid": record.get("MRGID"),
        "name": record.get("preferredGazetteerName"),
        "place_type": record.get("placeType"),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "min_latitude": record.get("minLatitude"),
        "min_longitude": record.get("minLongitude"),
        "max_latitude": record.get("maxLatitude"),
        "max_longitude": record.get("maxLongitude"),
    }
