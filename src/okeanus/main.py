"""FastAPI application entry point."""

from fastapi import FastAPI

from okeanus import __version__

app = FastAPI(
    title="Okeanus",
    description="Unified Ocean Intelligence Platform",
    version=__version__,
)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}
