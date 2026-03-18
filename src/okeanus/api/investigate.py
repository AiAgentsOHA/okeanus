"""Investigation API — start, poll, and stream recursive investigations."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from okeanus.config import settings
from okeanus.ml.llm.investigator import (
    InvestigationReport,
    get_investigation,
    start_investigation,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml", tags=["ml"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class InvestigateRequest(BaseModel):
    question: str = Field(..., min_length=10, description="The question to investigate")
    max_depth: int = Field(3, ge=1, le=4, description="Max recursion depth (1-4)")


class InvestigateResponse(BaseModel):
    investigation_id: str
    status: str
    message: str


class InvestigationStatusResponse(BaseModel):
    id: str
    question: str
    status: str
    progress: list[dict]
    tasks_total: int
    tasks_completed: int
    findings_total: int
    report: InvestigationReport | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(req: InvestigateRequest) -> InvestigateResponse:
    """Start a recursive investigation. Returns immediately with an ID for polling."""
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    investigation = await start_investigation(
        question=req.question,
        max_depth=req.max_depth,
    )

    return InvestigateResponse(
        investigation_id=investigation.id,
        status=investigation.status.value,
        message=f"Investigation started. Poll GET /ml/investigate/{investigation.id} for results.",
    )


@router.get("/investigate/{investigation_id}", response_model=InvestigationStatusResponse)
async def get_investigation_status(investigation_id: str) -> InvestigationStatusResponse:
    """Poll investigation status and results."""
    investigation = get_investigation(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    tasks_completed = sum(
        1 for t in investigation.tasks.values() if t.status.value == "completed"
    )
    findings_total = sum(len(t.findings) for t in investigation.tasks.values())

    return InvestigationStatusResponse(
        id=investigation.id,
        question=investigation.question,
        status=investigation.status.value,
        progress=investigation.progress_log,
        tasks_total=len(investigation.tasks),
        tasks_completed=tasks_completed,
        findings_total=findings_total,
        report=investigation.report,
    )


@router.get("/investigate/{investigation_id}/stream")
async def stream_investigation(investigation_id: str):
    """SSE stream of investigation progress updates."""
    investigation = get_investigation(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    async def event_generator():
        last_index = 0
        while True:
            # Yield any new progress entries
            current_log = investigation.progress_log
            if len(current_log) > last_index:
                for entry in current_log[last_index:]:
                    import json

                    yield {"event": entry["event"], "data": json.dumps(entry)}
                last_index = len(current_log)

            # Check if investigation is done
            if investigation.status.value in ("completed", "failed"):
                import json

                yield {
                    "event": "done",
                    "data": json.dumps({
                        "status": investigation.status.value,
                        "tasks_total": len(investigation.tasks),
                        "findings_total": sum(
                            len(t.findings) for t in investigation.tasks.values()
                        ),
                    }),
                }
                break

            await asyncio.sleep(1.0)

    return EventSourceResponse(event_generator())
