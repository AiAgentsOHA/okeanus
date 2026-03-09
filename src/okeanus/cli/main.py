"""CLI entry point for Okeanus."""

import click


@click.group()
@click.version_option(package_name="okeanus")
def cli() -> None:
    """Okeanus -- Unified Ocean Intelligence Platform."""


@cli.command()
def serve() -> None:
    """Start the API server."""
    import uvicorn

    uvicorn.run("okeanus.main:app", host="0.0.0.0", port=8000, reload=True)
