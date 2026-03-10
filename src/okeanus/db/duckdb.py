"""DuckDB analytics connection for fast analytical queries.

DuckDB runs in-process and can query Parquet files directly.  The optional
``postgres_scanner`` extension lets it read live PostGIS tables for hybrid
OLTP/OLAP workflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from okeanus.config import settings


def _ensure_data_dir() -> str:
    """Create the parent directory for the DuckDB database file."""
    db_path = Path(settings.duckdb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection with common extensions loaded.

    The connection is configured with:
    - ``spatial`` extension for geometry operations
    - ``postgres_scanner`` when a DATABASE_URL is available
    """
    db_path = _ensure_data_dir()
    conn = duckdb.connect(db_path)

    # Load spatial extension for geometry support
    conn.execute("INSTALL spatial; LOAD spatial;")

    # Attach PostGIS if DATABASE_URL is set (convert async URL to sync for DuckDB)
    pg_url = settings.database_url
    if pg_url:
        sync_url = pg_url.replace("+asyncpg", "").replace("+psycopg", "")
        try:
            conn.execute("INSTALL postgres; LOAD postgres;")
            conn.execute(f"ATTACH '{sync_url}' AS pg (TYPE POSTGRES, READ_ONLY);")
        except duckdb.Error:
            # postgres_scanner may not be available in all environments
            pass

    return conn


def analytical_query(sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
    """Execute an analytical SQL query and return all rows.

    Parameters
    ----------
    sql:
        DuckDB-compatible SQL.  Can reference Parquet files via
        ``read_parquet('path')`` or attached PostgreSQL tables via
        ``pg.public.observations``.
    params:
        Optional positional parameters for the query.

    Returns
    -------
    list[tuple]
        All result rows as a list of tuples.
    """
    conn = get_connection()
    try:
        if params:
            result = conn.execute(sql, params)
        else:
            result = conn.execute(sql)
        return result.fetchall()
    finally:
        conn.close()


def export_to_parquet(
    sql: str,
    output_path: str,
    params: list[Any] | None = None,
) -> Path:
    """Execute a query and write the result set to a Parquet file.

    Parameters
    ----------
    sql:
        Query whose results should be exported.
    output_path:
        Filesystem path for the output Parquet file.
    params:
        Optional positional parameters for the query.

    Returns
    -------
    Path
        The absolute path to the written Parquet file.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        copy_sql = f"COPY ({sql}) TO '{out}' (FORMAT PARQUET)"
        if params:
            conn.execute(copy_sql, params)
        else:
            conn.execute(copy_sql)
        return out.resolve()
    finally:
        conn.close()
