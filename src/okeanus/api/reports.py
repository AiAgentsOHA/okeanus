"""Intelligence report generation API endpoints.

Generates comprehensive HTML reports for vessels, areas, encounters,
and risk assessments.  Reports can be viewed directly in a browser
or converted to PDF via print.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from okeanus.reports.generator import (
    generate_area_report,
    generate_encounter_report,
    generate_risk_report,
    generate_vessel_profile,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/vessel/{mmsi}", response_class=HTMLResponse)
async def vessel_profile_report(mmsi: int) -> HTMLResponse:
    """Generate a comprehensive vessel profile intelligence report.

    Returns an HTML document with vessel identity, risk assessment,
    behavioral analysis, voyage history, and encounter records.
    Suitable for direct viewing or print-to-PDF.
    """
    html = await generate_vessel_profile(mmsi)
    return HTMLResponse(content=html)


@router.get("/risk/{mmsi}", response_class=HTMLResponse)
async def vessel_risk_report(mmsi: int) -> HTMLResponse:
    """Generate a detailed risk assessment report for a vessel.

    Returns an HTML document with composite risk score, individual
    factor breakdown, evidence items, and risk meter visualizations.
    """
    html = await generate_risk_report(mmsi)
    return HTMLResponse(content=html)


@router.get("/area", response_class=HTMLResponse)
async def area_activity_report(
    bbox: Annotated[
        str,
        Query(
            description="Bounding box: west,south,east,north",
            pattern=r"^-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*,-?\d+\.?\d*$",
        ),
    ],
    time_start: Annotated[datetime, Query(description="Start time (ISO 8601)")],
    time_end: Annotated[datetime, Query(description="End time (ISO 8601)")],
) -> HTMLResponse:
    """Generate an area activity intelligence report.

    Analyzes all vessel activity within a geographic bounding box and
    time window.  Returns an HTML document with vessel counts, encounter
    detection, risk rankings, and activity summary.
    """
    w, s, e, n = [float(x) for x in bbox.split(",")]
    html = await generate_area_report(
        bbox=(w, s, e, n), time_start=time_start, time_end=time_end
    )
    return HTMLResponse(content=html)


@router.post("/encounter", response_class=HTMLResponse)
async def encounter_detail_report(encounter_data: dict[str, Any]) -> HTMLResponse:
    """Generate a detailed encounter analysis report.

    Accepts encounter data (as returned by /ml/behavioral/encounters)
    and renders a comprehensive HTML analysis including vessel details,
    risk indicators, and timeline.
    """
    html = await generate_encounter_report(encounter_data)
    return HTMLResponse(content=html)


@router.get("/encounter/{mmsi}", response_class=HTMLResponse)
async def vessel_encounter_report(
    mmsi: int,
    time_start: Annotated[datetime | None, Query(description="Start time")] = None,
    time_end: Annotated[datetime | None, Query(description="End time")] = None,
) -> HTMLResponse:
    """Generate encounter report for a specific vessel's most recent encounter."""
    from okeanus.ml.behavioral.encounters import detect_encounters_for_vessel

    encounters = await detect_encounters_for_vessel(
        mmsi=mmsi, time_start=time_start, time_end=time_end
    )

    if not encounters:
        from okeanus.reports.templates import _footer, _header

        html = _header(
            title=f"Encounter Report — MMSI {mmsi}",
            subtitle="No encounters found",
            meta_items=[("MMSI", str(mmsi))],
        )
        html += '<div class="section"><div class="card"><p>No encounters detected for this vessel in the specified time period.</p></div></div>'
        html += _footer()
        return HTMLResponse(content=html)

    # Report on the most recent encounter
    latest = encounters[0].to_dict()
    html = await generate_encounter_report(latest)
    return HTMLResponse(content=html)
