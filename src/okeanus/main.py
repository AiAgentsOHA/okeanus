"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from okeanus import __version__
from okeanus.api import health, ingest, observations, regions, vessels

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    logger.info("Okeanus %s starting up", __version__)
    # Database engine is created at import time in db.postgres;
    # we just verify the import succeeds here.
    try:
        from okeanus.db.postgres import engine  # noqa: F401

        logger.info("Database engine initialised")
    except Exception as exc:
        logger.warning("Database not available, running in mock mode: %s", exc)
    yield
    # Shutdown: dispose of the database engine if it was created
    try:
        from okeanus.db.postgres import engine

        await engine.dispose()
        logger.info("Database engine disposed")
    except Exception:
        pass


app = FastAPI(
    title="Okeanus",
    description="Unified Ocean Intelligence Platform -- aggregating ocean data from "
    "AIS, satellite, acoustic, and biological sources into a single queryable API.",
    version=__version__,
    lifespan=lifespan,
)

# CORS -- allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(observations.router)
app.include_router(vessels.router)
app.include_router(regions.router)
app.include_router(ingest.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
