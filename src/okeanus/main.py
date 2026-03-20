"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from okeanus import __version__

from okeanus.api import analytics, dashboard, economy, health, ingest, observations, query, regions, vessels
from okeanus.api.behavioral import router as behavioral_router
from okeanus.api.geospatial import router as geospatial_router
from okeanus.api.lineage import router as lineage_router
from okeanus.api.reports import router as reports_router
from okeanus.api.risk import router as risk_router
from okeanus.ml.anomaly import router as anomaly_router
from okeanus.ml.embeddings import router as embeddings_router
from okeanus.ml.forecast import router as forecast_router
from okeanus.api.investigate import router as investigate_router
from okeanus.auth.routes import router as auth_router
from okeanus.geofence.routes import router as geofence_router
from okeanus.ml.llm.chat import router as chat_router
from okeanus.api.alerts import router as alerts_api_router
from okeanus.config import settings
from okeanus.streaming import alerts, vessels_ws
from okeanus.streaming import status as streaming_status

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

    # --- Streaming infrastructure ---
    ais_task = None
    scheduler = None
    try:
        from okeanus.streaming.ais_ingester import AISIngester
        from okeanus.streaming.redis_pool import close_redis, get_redis
        from okeanus.streaming.scheduler import DataRefreshScheduler

        await get_redis()  # Verify Redis connection
        logger.info("Redis connected")

        if settings.ais_stream_enabled:
            ingester = AISIngester()
            ais_task = asyncio.create_task(ingester.start())
            logger.info("AIS stream ingester started")

        if settings.scheduler_enabled:
            scheduler = DataRefreshScheduler()
            # Register jobs here as needed
            await scheduler.start()
            streaming_status.set_scheduler(scheduler)
            logger.info("Data refresh scheduler started")

    except Exception as exc:
        logger.warning("Streaming infrastructure not available: %s", exc)

    yield

    # Shutdown streaming
    if ais_task:
        try:
            await ingester.stop()  # type: ignore[union-attr]
        except Exception:
            pass
        ais_task.cancel()
        try:
            await ais_task
        except asyncio.CancelledError:
            pass
    if scheduler:
        await scheduler.stop()
    try:
        from okeanus.streaming.redis_pool import close_redis

        await close_redis()
    except Exception:
        pass

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
app.include_router(auth_router)
app.include_router(health.router)
app.include_router(dashboard.router)
app.include_router(observations.router)
app.include_router(vessels.router)
app.include_router(regions.router)
app.include_router(ingest.router)
app.include_router(economy.router)
app.include_router(query.router)
app.include_router(analytics.router)

# Streaming routers
app.include_router(vessels_ws.router)
app.include_router(alerts.router)
app.include_router(streaming_status.router)

# ML routers
app.include_router(chat_router)
app.include_router(anomaly_router)
app.include_router(forecast_router)
app.include_router(embeddings_router)
app.include_router(investigate_router)
app.include_router(behavioral_router)
app.include_router(geofence_router)
app.include_router(risk_router)
app.include_router(reports_router)
app.include_router(geospatial_router)
app.include_router(lineage_router)
app.include_router(alerts_api_router)

# Intelligence layer
try:
    from okeanus.ml.engine.routes import router as intelligence_router
    app.include_router(intelligence_router)
except ImportError:
    pass  # ml extras not installed


# Static frontend (Deck.gl map)
import pathlib as _pathlib  # noqa: E402

_frontend_dir = _pathlib.Path(__file__).resolve().parent.parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/app", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
    logger.info("Frontend mounted at /app from %s", _frontend_dir)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    from fastapi import HTTPException as _HTTPException
    from starlette.exceptions import HTTPException as _StarletteHTTPException

    # Let HTTP exceptions pass through with their proper status codes
    if isinstance(exc, (_HTTPException, _StarletteHTTPException)):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
