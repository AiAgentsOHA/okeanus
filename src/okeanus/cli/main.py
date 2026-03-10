"""CLI entry point for Okeanus."""

import click

from okeanus import __version__
from okeanus.config import settings


@click.group()
@click.version_option(package_name="okeanus")
def cli() -> None:
    """Okeanus -- Unified Ocean Intelligence Platform."""


@cli.command()
@click.option("--host", default=None, help="Bind host (default from config)")
@click.option("--port", default=None, type=int, help="Bind port (default from config)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host: str | None, port: int | None, reload: bool) -> None:
    """Start the API server."""
    import uvicorn

    uvicorn.run(
        "okeanus.main:app",
        host=host or settings.api_host,
        port=port or settings.api_port,
        reload=reload or settings.api_reload,
        log_level=settings.log_level.lower(),
    )


@cli.command()
def sources() -> None:
    """List available data sources and their configuration status."""
    click.echo(f"Okeanus v{__version__} -- Data Sources\n")
    for source in settings.configured_sources():
        if source["configured"]:
            status = click.style("ready", fg="green")
        else:
            status = click.style(f"needs {source['auth']}", fg="yellow")
        click.echo(f"  {source['name']:<25} {status}")


@cli.command()
def health() -> None:
    """Check system health by hitting the local API."""
    import httpx

    url = f"http://{settings.api_host}:{settings.api_port}/health"
    try:
        resp = httpx.get(url, timeout=5.0)
        data = resp.json()
        status_color = "green" if data.get("status") == "ok" else "red"
        click.echo(f"Status:  {click.style(data['status'], fg=status_color)}")
        click.echo(f"Version: {data.get('version', 'unknown')}")
    except httpx.RequestError:
        click.echo(click.style("Error: Could not reach API server", fg="red"))
        raise SystemExit(1)


@cli.command()
@click.argument("source")
@click.option("--bbox", default=None, help="Bounding box: west,south,east,north")
@click.option("--time-start", default=None, help="Start time (ISO 8601)")
@click.option("--time-end", default=None, help="End time (ISO 8601)")
@click.option("--limit", default=500, help="Max records to fetch")
@click.option("--no-store", is_flag=True, help="Don't store in PostGIS")
def fetch(
    source: str,
    bbox: str | None,
    time_start: str | None,
    time_end: str | None,
    limit: int,
    no_store: bool,
) -> None:
    """Fetch data from a source adapter and store in PostGIS.

    SOURCE is the adapter name (obis, gbif, argovis, noaa_coops, erddap, etc.)
    """
    import asyncio

    from okeanus.api.ingest import _build_adapter, _dict_to_observation
    from okeanus.db.postgres import async_session_factory

    async def _run() -> int:
        adapter = _build_adapter(source)
        if adapter is None:
            from okeanus.adapters import ADAPTER_REGISTRY

            available = sorted(ADAPTER_REGISTRY.keys())
            click.echo(click.style(f"Unknown source: {source}", fg="red"))
            click.echo(f"Available: {', '.join(available)}")
            raise SystemExit(1)

        from datetime import UTC, datetime, timedelta

        ts = (
            datetime.fromisoformat(time_start)
            if time_start
            else datetime.now(UTC) - timedelta(days=7)
        )
        te = (
            datetime.fromisoformat(time_end)
            if time_end
            else datetime.now(UTC)
        )
        b = (
            tuple(float(x) for x in bbox.split(","))
            if bbox
            else (-10.0, 35.0, 0.0, 45.0)
        )

        click.echo(f"Fetching from '{source}' bbox={b} {ts} -> {te}")
        records = await adapter.fetch(b, ts, te, limit=limit)
        click.echo(f"  Got {len(records)} records")

        if records and not no_store:
            observations = [_dict_to_observation(r.copy()) for r in records]
            async with async_session_factory() as session:
                session.add_all(observations)
                await session.commit()
            msg = f"  Stored {len(observations)} observations in PostGIS"
            click.echo(click.style(msg, fg="green"))
        return len(records)

    asyncio.run(_run())
