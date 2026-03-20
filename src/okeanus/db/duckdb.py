"""DuckDB analytics connection for fast analytical queries.

DuckDB runs in-process and can query Parquet files directly.  The optional
``postgres_scanner`` extension lets it read live PostGIS tables for hybrid
OLTP/OLAP workflows.

After calling :func:`sync_from_postgres`, all analytical functions query
*local* DuckDB tables for maximum speed.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from okeanus.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton connection
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_conn: duckdb.DuckDBPyConnection | None = None


def _ensure_data_dir() -> str:
    """Create the parent directory for the DuckDB database file."""
    db_path = Path(settings.duckdb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a singleton DuckDB connection with common extensions loaded.

    The connection is configured with:
    - ``spatial`` extension for geometry operations
    - ``postgres_scanner`` when a DATABASE_URL is available
    """
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is not None:
            return _conn
        db_path = _ensure_data_dir()
        conn = duckdb.connect(db_path)

        # Load spatial extension for geometry support
        conn.execute("INSTALL spatial; LOAD spatial;")

        # Attach PostGIS if DATABASE_URL is set
        pg_url = settings.database_url
        if pg_url:
            sync_url = pg_url.replace("+asyncpg", "").replace("+psycopg", "")
            try:
                conn.execute("INSTALL postgres; LOAD postgres;")
                conn.execute(
                    f"ATTACH '{sync_url}' AS pg (TYPE POSTGRES, READ_ONLY);"
                )
            except duckdb.Error:
                # postgres_scanner may not be available in all environments
                pass

        _conn = conn
        return _conn


# ---------------------------------------------------------------------------
# Generic helpers (kept from original API)
# ---------------------------------------------------------------------------


def analytical_query(
    sql: str, params: list[Any] | None = None
) -> list[tuple[Any, ...]]:
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
    if params:
        result = conn.execute(sql, params)
    else:
        result = conn.execute(sql)
    return result.fetchall()


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
    copy_sql = f"COPY ({sql}) TO '{out}' (FORMAT PARQUET)"
    if params:
        conn.execute(copy_sql, params)
    else:
        conn.execute(copy_sql)
    return out.resolve()


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

_SYNC_TABLES = [
    "time_series",
    "entities",
    "flows",
    "events",
    "assessments",
    "claims",
    "relationships",
    "observations",
]


def sync_from_postgres() -> dict[str, int]:
    """Sync all economy tables from PostgreSQL into local DuckDB tables.

    Returns
    -------
    dict[str, int]
        Mapping of table name to row count after sync.
    """
    conn = get_connection()
    counts: dict[str, int] = {}
    for table in _SYNC_TABLES:
        conn.execute(
            f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM pg.public.{table}"
        )
        row = conn.execute(f"SELECT count(*) FROM {table}").fetchone()
        counts[table] = row[0] if row else 0
        logger.info("Synced %s: %d rows", table, counts[table])
    return counts


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rows_to_dicts(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute *sql* and return results as a list of dicts."""
    if params:
        result = conn.execute(sql, params)
    else:
        result = conn.execute(sql)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


# ===================================================================
# TimeSeries analytics (6)
# ===================================================================


def ts_rollup(
    code: str | None = None,
    commodity: str | None = None,
    country: str | None = None,
    source_name: str | None = None,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
    aggregation: str = "monthly",
) -> list[dict[str, Any]]:
    """Aggregate time series data via DuckDB for analytics dashboards."""
    valid_aggs = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",
    }
    trunc = valid_aggs.get(aggregation, "month")

    conditions: list[str] = []
    params: list[Any] = []
    if code:
        conditions.append("code = ?")
        params.append(code)
    if commodity:
        conditions.append("commodity = ?")
        params.append(commodity)
    if country:
        conditions.append("country = ?")
        params.append(country)
    if source_name:
        conditions.append("source_name = ?")
        params.append(source_name)
    if time_start:
        conditions.append("timestamp >= ?")
        params.append(time_start)
    if time_end:
        conditions.append("timestamp <= ?")
        params.append(time_end)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            date_trunc('{trunc}', timestamp) AS period,
            code,
            commodity,
            country,
            avg(value)   AS avg_value,
            min(value)   AS min_value,
            max(value)   AS max_value,
            count(*)     AS count
        FROM time_series
        {where}
        GROUP BY period, code, commodity, country
        ORDER BY period DESC
    """
    return _rows_to_dicts(get_connection(), sql, params or None)


def ts_moving_average(
    code: str,
    window: int = 7,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Rolling average and standard deviation over a windowed range."""
    conditions: list[str] = ["code = ?"]
    params: list[Any] = [code]
    if time_start:
        conditions.append("timestamp >= ?")
        params.append(time_start)
    if time_end:
        conditions.append("timestamp <= ?")
        params.append(time_end)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            timestamp,
            value,
            avg(value) OVER (
                ORDER BY timestamp
                ROWS BETWEEN {int(window) - 1} PRECEDING AND CURRENT ROW
            ) AS moving_avg,
            stddev_pop(value) OVER (
                ORDER BY timestamp
                ROWS BETWEEN {int(window) - 1} PRECEDING AND CURRENT ROW
            ) AS moving_stddev
        FROM time_series
        {where}
        ORDER BY timestamp
    """
    return _rows_to_dicts(get_connection(), sql, params)


def ts_yoy_change(
    code: str,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Year-over-year percentage change.

    Computes lag at 12 periods for monthly data, or 365 for daily data.
    Uses monthly rollup internally for a clean comparison.
    """
    conditions: list[str] = ["code = ?"]
    params: list[Any] = [code]
    if time_start:
        conditions.append("timestamp >= ?")
        params.append(time_start)
    if time_end:
        conditions.append("timestamp <= ?")
        params.append(time_end)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        WITH monthly AS (
            SELECT
                date_trunc('month', timestamp) AS period,
                avg(value) AS avg_value
            FROM time_series
            {where}
            GROUP BY period
        )
        SELECT
            period,
            avg_value,
            lag(avg_value, 12) OVER (ORDER BY period) AS prev_year_value,
            CASE
                WHEN lag(avg_value, 12) OVER (ORDER BY period) IS NOT NULL
                     AND lag(avg_value, 12) OVER (ORDER BY period) != 0
                THEN ((avg_value - lag(avg_value, 12) OVER (ORDER BY period))
                      / lag(avg_value, 12) OVER (ORDER BY period)) * 100
                ELSE NULL
            END AS yoy_pct_change
        FROM monthly
        ORDER BY period
    """
    return _rows_to_dicts(get_connection(), sql, params)


def ts_volatility(
    code: str,
    window: int = 30,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Rolling standard deviation and percentage returns."""
    conditions: list[str] = ["code = ?"]
    params: list[Any] = [code]
    if time_start:
        conditions.append("timestamp >= ?")
        params.append(time_start)
    if time_end:
        conditions.append("timestamp <= ?")
        params.append(time_end)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        WITH base AS (
            SELECT
                timestamp,
                value,
                CASE
                    WHEN lag(value) OVER (ORDER BY timestamp) IS NOT NULL
                         AND lag(value) OVER (ORDER BY timestamp) != 0
                    THEN (value - lag(value) OVER (ORDER BY timestamp))
                         / lag(value) OVER (ORDER BY timestamp)
                    ELSE NULL
                END AS pct_return
            FROM time_series
            {where}
        )
        SELECT
            timestamp,
            value,
            pct_return,
            stddev_pop(value) OVER (
                ORDER BY timestamp
                ROWS BETWEEN {int(window) - 1} PRECEDING AND CURRENT ROW
            ) AS rolling_stddev,
            stddev_pop(pct_return) OVER (
                ORDER BY timestamp
                ROWS BETWEEN {int(window) - 1} PRECEDING AND CURRENT ROW
            ) AS rolling_return_vol
        FROM base
        ORDER BY timestamp
    """
    return _rows_to_dicts(get_connection(), sql, params)


def ts_correlation(
    code_a: str,
    code_b: str,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Pearson correlation, regression slope, and R-squared between two series."""
    conditions_a: list[str] = ["a.code = ?"]
    conditions_b: list[str] = ["b.code = ?"]
    params: list[Any] = [code_a, code_b]
    join_conds: list[str] = []
    if time_start:
        join_conds.append("a.timestamp >= ?")
        params.append(time_start)
    if time_end:
        join_conds.append("a.timestamp <= ?")
        params.append(time_end)

    time_filter = (" AND " + " AND ".join(join_conds)) if join_conds else ""

    sql = f"""
        WITH series_a AS (
            SELECT date_trunc('month', timestamp) AS period,
                   avg(value) AS value_a
            FROM time_series
            WHERE code = ?
            GROUP BY period
        ),
        series_b AS (
            SELECT date_trunc('month', timestamp) AS period,
                   avg(value) AS value_b
            FROM time_series
            WHERE code = ?
            GROUP BY period
        ),
        joined AS (
            SELECT a.period, a.value_a, b.value_b
            FROM series_a a
            INNER JOIN series_b b ON a.period = b.period
        )
        SELECT
            corr(value_a, value_b)       AS pearson_r,
            regr_slope(value_a, value_b) AS slope,
            regr_r2(value_a, value_b)    AS r_squared,
            count(*)                     AS n_periods
        FROM joined
    """
    # Build params for series_a WHERE and series_b WHERE
    corr_params: list[Any] = [code_a, code_b]
    return _rows_to_dicts(get_connection(), sql, corr_params)


def ts_trend(
    code: str,
    window: int = 12,
    time_start: datetime | None = None,
    time_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Centered moving average trend decomposition with regression slope."""
    conditions: list[str] = ["code = ?"]
    params: list[Any] = [code]
    if time_start:
        conditions.append("timestamp >= ?")
        params.append(time_start)
    if time_end:
        conditions.append("timestamp <= ?")
        params.append(time_end)

    where = "WHERE " + " AND ".join(conditions)
    half = int(window) // 2

    sql = f"""
        WITH monthly AS (
            SELECT
                date_trunc('month', timestamp) AS period,
                avg(value) AS avg_value
            FROM time_series
            {where}
            GROUP BY period
        ),
        with_trend AS (
            SELECT
                period,
                avg_value,
                avg(avg_value) OVER (
                    ORDER BY period
                    ROWS BETWEEN {half} PRECEDING AND {half} FOLLOWING
                ) AS trend,
                row_number() OVER (ORDER BY period) AS rn
            FROM monthly
        )
        SELECT
            period,
            avg_value,
            trend,
            avg_value - trend AS residual,
            regr_slope(avg_value, rn) OVER () AS overall_slope
        FROM with_trend
        ORDER BY period
    """
    return _rows_to_dicts(get_connection(), sql, params)


# ===================================================================
# Entity analytics (3)
# ===================================================================


def entity_distribution(
    group_by: str = "entity_type",
) -> list[dict[str, Any]]:
    """Count entities by a grouping column (entity_type, country, or sector)."""
    allowed = {"entity_type", "country", "sector"}
    col = group_by if group_by in allowed else "entity_type"

    sql = f"""
        SELECT
            {col}   AS group_key,
            count(*) AS count
        FROM entities
        WHERE {col} IS NOT NULL
        GROUP BY {col}
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql)


def entity_connectivity() -> list[dict[str, Any]]:
    """Degree centrality: count inbound + outbound edges per entity."""
    sql = """
        WITH out_deg AS (
            SELECT source_entity_id AS entity_id, count(*) AS out_degree
            FROM relationships
            GROUP BY source_entity_id
        ),
        in_deg AS (
            SELECT dest_entity_id AS entity_id, count(*) AS in_degree
            FROM relationships
            GROUP BY dest_entity_id
        )
        SELECT
            e.id                      AS entity_id,
            e.name                    AS entity_name,
            e.entity_type,
            coalesce(o.out_degree, 0) AS out_degree,
            coalesce(i.in_degree, 0)  AS in_degree,
            coalesce(o.out_degree, 0) + coalesce(i.in_degree, 0) AS total_degree
        FROM entities e
        LEFT JOIN out_deg o ON o.entity_id = e.id
        LEFT JOIN in_deg  i ON i.entity_id = e.id
        ORDER BY total_degree DESC
    """
    return _rows_to_dicts(get_connection(), sql)


def entity_density(
    resolution: float = 1.0,
) -> list[dict[str, Any]]:
    """Geographic density via floor-based lat/lon bins.

    Uses DuckDB spatial ``ST_X`` / ``ST_Y`` on the geometry column.
    Entities without geometry are excluded.
    """
    res = float(resolution)
    sql = f"""
        SELECT
            floor(ST_Y(geometry) / {res}) * {res} AS lat_bin,
            floor(ST_X(geometry) / {res}) * {res} AS lon_bin,
            count(*) AS count
        FROM entities
        WHERE geometry IS NOT NULL
        GROUP BY lat_bin, lon_bin
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql)


# ===================================================================
# Flow analytics (3)
# ===================================================================


def flow_trade_balance(
    time_start: datetime | None = None,
    time_end: datetime | None = None,
) -> list[dict[str, Any]]:
    """Net trade by country pair (joins entities for country)."""
    conditions: list[str] = []
    params: list[Any] = []
    if time_start:
        conditions.append("f.timestamp >= ?")
        params.append(time_start)
    if time_end:
        conditions.append("f.timestamp <= ?")
        params.append(time_end)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            src.country AS source_country,
            dst.country AS dest_country,
            f.commodity,
            sum(f.amount) AS total_amount,
            f.currency,
            count(*)      AS flow_count
        FROM flows f
        LEFT JOIN entities src ON f.source_entity_id = src.id
        LEFT JOIN entities dst ON f.dest_entity_id   = dst.id
        {where}
        GROUP BY src.country, dst.country, f.commodity, f.currency
        ORDER BY total_amount DESC NULLS LAST
    """
    return _rows_to_dicts(get_connection(), sql, params or None)


def flow_top_n(
    n: int = 20,
    flow_type: str | None = None,
) -> list[dict[str, Any]]:
    """Top flows by amount for Sankey diagrams."""
    conditions: list[str] = ["f.amount IS NOT NULL"]
    params: list[Any] = []
    if flow_type:
        conditions.append("f.flow_type = ?")
        params.append(flow_type)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            f.id,
            f.flow_type,
            src.name     AS source_name,
            dst.name     AS dest_name,
            f.amount,
            f.currency,
            f.commodity,
            f.timestamp
        FROM flows f
        LEFT JOIN entities src ON f.source_entity_id = src.id
        LEFT JOIN entities dst ON f.dest_entity_id   = dst.id
        {where}
        ORDER BY f.amount DESC
        LIMIT {int(n)}
    """
    return _rows_to_dicts(get_connection(), sql, params or None)


def flow_network_stats() -> list[dict[str, Any]]:
    """Network summary: total nodes, edges, average degree."""
    sql = """
        WITH edge_entities AS (
            SELECT DISTINCT source_entity_id AS eid FROM flows
            WHERE source_entity_id IS NOT NULL
            UNION
            SELECT DISTINCT dest_entity_id AS eid FROM flows
            WHERE dest_entity_id IS NOT NULL
        )
        SELECT
            (SELECT count(*) FROM edge_entities) AS total_nodes,
            (SELECT count(*) FROM flows)         AS total_edges,
            CASE
                WHEN (SELECT count(*) FROM edge_entities) > 0
                THEN (SELECT count(*) FROM flows)::DOUBLE
                     / (SELECT count(*) FROM edge_entities)
                ELSE 0
            END AS avg_degree
    """
    return _rows_to_dicts(get_connection(), sql)


# ===================================================================
# Event analytics (3)
# ===================================================================


def event_frequency(
    aggregation: str = "monthly",
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Frequency histogram by event type and time period."""
    valid_aggs = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",
    }
    trunc = valid_aggs.get(aggregation, "month")

    conditions: list[str] = []
    params: list[Any] = []
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            date_trunc('{trunc}', timestamp) AS period,
            event_type,
            count(*)                         AS count
        FROM events
        {where}
        GROUP BY period, event_type
        ORDER BY period DESC, count DESC
    """
    return _rows_to_dicts(get_connection(), sql, params or None)


def event_severity_trend(
    aggregation: str = "monthly",
) -> list[dict[str, Any]]:
    """Severity percentiles over time (economic_impact)."""
    valid_aggs = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",
    }
    trunc = valid_aggs.get(aggregation, "month")

    sql = f"""
        SELECT
            date_trunc('{trunc}', timestamp)           AS period,
            count(*)                                    AS event_count,
            avg(economic_impact)                        AS avg_impact,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY economic_impact) AS p25_impact,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY economic_impact) AS p50_impact,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY economic_impact) AS p75_impact,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY economic_impact) AS p95_impact
        FROM events
        WHERE economic_impact IS NOT NULL
        GROUP BY period
        ORDER BY period DESC
    """
    return _rows_to_dicts(get_connection(), sql)


def event_economic_correlation(
    ts_code: str,
    aggregation: str = "monthly",
) -> list[dict[str, Any]]:
    """Join event counts with timeseries values by period."""
    valid_aggs = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",
    }
    trunc = valid_aggs.get(aggregation, "month")

    sql = f"""
        WITH event_counts AS (
            SELECT
                date_trunc('{trunc}', timestamp) AS period,
                count(*)                         AS event_count,
                avg(economic_impact)             AS avg_impact
            FROM events
            GROUP BY period
        ),
        ts_vals AS (
            SELECT
                date_trunc('{trunc}', timestamp) AS period,
                avg(value)                       AS avg_value
            FROM time_series
            WHERE code = ?
            GROUP BY period
        )
        SELECT
            coalesce(e.period, t.period) AS period,
            e.event_count,
            e.avg_impact,
            t.avg_value                  AS ts_value,
            corr(e.event_count, t.avg_value) OVER () AS correlation
        FROM event_counts e
        FULL OUTER JOIN ts_vals t ON e.period = t.period
        ORDER BY period
    """
    return _rows_to_dicts(get_connection(), sql, [ts_code])


# ===================================================================
# Assessment analytics (4)
# ===================================================================


def assessment_distribution(
    metric_code: str,
) -> list[dict[str, Any]]:
    """Score percentiles, mean, and stddev for a metric."""
    sql = """
        SELECT
            metric_code,
            count(*)                                AS count,
            avg(score_numeric)                      AS mean,
            stddev_pop(score_numeric)               AS stddev,
            min(score_numeric)                      AS min_score,
            max(score_numeric)                      AS max_score,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY score_numeric) AS p25,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY score_numeric) AS median,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY score_numeric) AS p75
        FROM assessments
        WHERE metric_code = ? AND score_numeric IS NOT NULL
        GROUP BY metric_code
    """
    return _rows_to_dicts(get_connection(), sql, [metric_code])


def assessment_ranking(
    metric_code: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Entity ranking by score with QUALIFY row_number()."""
    sql = f"""
        SELECT
            a.entity_id,
            e.name          AS entity_name,
            e.entity_type,
            a.assessor,
            a.score_numeric,
            a.score_category,
            a.timestamp,
            row_number() OVER (
                PARTITION BY a.entity_id
                ORDER BY a.timestamp DESC NULLS LAST
            ) AS rn
        FROM assessments a
        LEFT JOIN entities e ON a.entity_id = e.id
        WHERE a.metric_code = ? AND a.score_numeric IS NOT NULL
        QUALIFY rn = 1
        ORDER BY a.score_numeric DESC
        LIMIT {int(limit)}
    """
    return _rows_to_dicts(get_connection(), sql, [metric_code])


def assessment_trend(
    metric_code: str,
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    """Score over time for a metric, optionally filtered to one entity."""
    conditions: list[str] = ["metric_code = ?"]
    params: list[Any] = [metric_code]
    if entity_id:
        conditions.append("entity_id = ?::UUID")
        params.append(entity_id)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            date_trunc('month', timestamp) AS period,
            entity_id,
            assessor,
            avg(score_numeric)             AS avg_score,
            count(*)                       AS count
        FROM assessments
        {where}
          AND timestamp IS NOT NULL
          AND score_numeric IS NOT NULL
        GROUP BY period, entity_id, assessor
        ORDER BY period
    """
    return _rows_to_dicts(get_connection(), sql, params)


def assessment_cross_compare(
    entity_id: str,
) -> list[dict[str, Any]]:
    """All assessor scores for one entity."""
    sql = """
        SELECT
            a.assessor,
            a.metric_code,
            a.score_numeric,
            a.score_category,
            a.confidence,
            a.trend,
            a.timestamp
        FROM assessments a
        WHERE a.entity_id = ?::UUID
        ORDER BY a.assessor, a.metric_code, a.timestamp DESC
    """
    return _rows_to_dicts(get_connection(), sql, [entity_id])


# ===================================================================
# Claim analytics (3)
# ===================================================================


def claim_delivery_stats() -> list[dict[str, Any]]:
    """Completion rates by status."""
    sql = """
        SELECT
            status,
            count(*)                              AS count,
            avg(progress_percent)                 AS avg_progress,
            count(*) FILTER (WHERE progress_percent >= 100) AS completed,
            count(*) * 100.0 / sum(count(*)) OVER () AS pct_of_total
        FROM claims
        GROUP BY status
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql)


def claim_deadline_analysis() -> list[dict[str, Any]]:
    """Counts by month plus overdue analysis."""
    sql = """
        SELECT
            date_trunc('month', deadline) AS deadline_month,
            count(*)                      AS total_claims,
            count(*) FILTER (
                WHERE deadline < current_timestamp AND coalesce(progress_percent, 0) < 100
            ) AS overdue,
            count(*) FILTER (
                WHERE coalesce(progress_percent, 0) >= 100
            ) AS completed,
            avg(progress_percent) AS avg_progress
        FROM claims
        WHERE deadline IS NOT NULL
        GROUP BY deadline_month
        ORDER BY deadline_month
    """
    return _rows_to_dicts(get_connection(), sql)


def claim_gap_analysis() -> list[dict[str, Any]]:
    """Target value vs progress percent gap."""
    sql = """
        SELECT
            id,
            name,
            status,
            target_value,
            target_unit,
            progress_percent,
            deadline,
            CASE
                WHEN target_value IS NOT NULL AND target_value > 0
                THEN target_value * (1.0 - coalesce(progress_percent, 0) / 100.0)
                ELSE NULL
            END AS remaining_value,
            CASE
                WHEN deadline IS NOT NULL
                THEN deadline - current_timestamp
                ELSE NULL
            END AS time_remaining
        FROM claims
        WHERE target_value IS NOT NULL
        ORDER BY remaining_value DESC NULLS LAST
    """
    return _rows_to_dicts(get_connection(), sql)


# ===================================================================
# Relationship analytics (3)
# ===================================================================


def relationship_degree_centrality(
    limit: int = 50,
) -> list[dict[str, Any]]:
    """In-degree + out-degree per entity from the relationships table."""
    sql = f"""
        WITH out_deg AS (
            SELECT source_entity_id AS entity_id, count(*) AS out_degree
            FROM relationships
            GROUP BY source_entity_id
        ),
        in_deg AS (
            SELECT dest_entity_id AS entity_id, count(*) AS in_degree
            FROM relationships
            GROUP BY dest_entity_id
        )
        SELECT
            e.id                      AS entity_id,
            e.name                    AS entity_name,
            e.entity_type,
            coalesce(o.out_degree, 0) AS out_degree,
            coalesce(i.in_degree, 0)  AS in_degree,
            coalesce(o.out_degree, 0) + coalesce(i.in_degree, 0) AS total_degree
        FROM entities e
        LEFT JOIN out_deg o ON o.entity_id = e.id
        LEFT JOIN in_deg  i ON i.entity_id = e.id
        WHERE coalesce(o.out_degree, 0) + coalesce(i.in_degree, 0) > 0
        ORDER BY total_degree DESC
        LIMIT {int(limit)}
    """
    return _rows_to_dicts(get_connection(), sql)


def relationship_components() -> list[dict[str, Any]]:
    """Connected components via recursive CTE (max depth 10)."""
    sql = """
        WITH RECURSIVE edges AS (
            SELECT source_entity_id AS a, dest_entity_id AS b
            FROM relationships
            UNION ALL
            SELECT dest_entity_id AS a, source_entity_id AS b
            FROM relationships
        ),
        components AS (
            SELECT a AS entity_id, a AS component_id, 0 AS depth
            FROM edges
            UNION
            SELECT e.b AS entity_id, c.component_id, c.depth + 1
            FROM components c
            JOIN edges e ON c.entity_id = e.a
            WHERE c.depth < 10
        ),
        canonical AS (
            SELECT entity_id, min(component_id) AS component_id
            FROM components
            GROUP BY entity_id
        )
        SELECT
            component_id,
            count(*)        AS size,
            array_agg(entity_id) AS entity_ids
        FROM canonical
        GROUP BY component_id
        ORDER BY size DESC
    """
    return _rows_to_dicts(get_connection(), sql)


def relationship_type_distribution() -> list[dict[str, Any]]:
    """Count by relationship_type."""
    sql = """
        SELECT
            relationship_type,
            count(*)                      AS count,
            count(DISTINCT source_entity_id) AS unique_sources,
            count(DISTINCT dest_entity_id)   AS unique_targets
        FROM relationships
        GROUP BY relationship_type
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql)


# ===================================================================
# Observation analytics (3)
# ===================================================================


def observation_temporal(
    aggregation: str = "daily",
    obs_type: str | None = None,
) -> list[dict[str, Any]]:
    """Count by period and observation type."""
    valid_aggs = {
        "daily": "day",
        "weekly": "week",
        "monthly": "month",
        "yearly": "year",
    }
    trunc = valid_aggs.get(aggregation, "day")

    conditions: list[str] = []
    params: list[Any] = []
    if obs_type:
        conditions.append("obs_type = ?")
        params.append(obs_type)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            date_trunc('{trunc}', timestamp) AS period,
            obs_type,
            count(*)                         AS count
        FROM observations
        {where}
        GROUP BY period, obs_type
        ORDER BY period DESC, count DESC
    """
    return _rows_to_dicts(get_connection(), sql, params or None)


def observation_spatial_grid(
    resolution: float = 1.0,
    obs_type: str | None = None,
) -> list[dict[str, Any]]:
    """Floor-based lat/lon binning for heatmap."""
    res = float(resolution)
    conditions: list[str] = ["geometry IS NOT NULL"]
    params: list[Any] = []
    if obs_type:
        conditions.append("obs_type = ?")
        params.append(obs_type)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            floor(ST_Y(geometry) / {res}) * {res} AS lat_bin,
            floor(ST_X(geometry) / {res}) * {res} AS lon_bin,
            count(*)                               AS count
        FROM observations
        {where}
        GROUP BY lat_bin, lon_bin
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql, params or None)


def observation_source_coverage() -> list[dict[str, Any]]:
    """Records per source_name with time range."""
    sql = """
        SELECT
            source_name,
            count(*)          AS record_count,
            min(timestamp)    AS earliest,
            max(timestamp)    AS latest,
            count(DISTINCT obs_type) AS obs_type_count
        FROM observations
        GROUP BY source_name
        ORDER BY record_count DESC
    """
    return _rows_to_dicts(get_connection(), sql)


# ===================================================================
# Spatial analytics (2)
# ===================================================================


def spatial_cluster_summary(
    resolution: float = 1.0,
) -> list[dict[str, Any]]:
    """Quick cluster summary using DuckDB spatial extension.

    Groups observations into geographic bins and returns bins
    with multiple sources as potential cluster candidates.
    """
    res = float(resolution)
    sql = f"""
        SELECT
            floor(ST_Y(geometry) / {res}) * {res} AS lat_bin,
            floor(ST_X(geometry) / {res}) * {res} AS lon_bin,
            count(*)                               AS count,
            count(DISTINCT source_name)            AS source_count,
            count(DISTINCT obs_type)               AS type_count,
            min(timestamp)                         AS earliest,
            max(timestamp)                         AS latest
        FROM observations
        WHERE geometry IS NOT NULL
        GROUP BY lat_bin, lon_bin
        HAVING count(*) >= 5
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql)


def observation_density_grid(
    resolution: float = 1.0,
    obs_type: str | None = None,
) -> list[dict[str, Any]]:
    """Grid-based density using DuckDB floor/group with normalized density."""
    res = float(resolution)
    conditions: list[str] = ["geometry IS NOT NULL"]
    params: list[Any] = []
    if obs_type:
        conditions.append("obs_type = ?")
        params.append(obs_type)

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        WITH grid AS (
            SELECT
                floor(ST_Y(geometry) / {res}) * {res} AS lat_bin,
                floor(ST_X(geometry) / {res}) * {res} AS lon_bin,
                count(*) AS count
            FROM observations
            {where}
            GROUP BY lat_bin, lon_bin
        )
        SELECT
            lat_bin,
            lon_bin,
            count,
            count * 1.0 / max(count) OVER () AS density
        FROM grid
        ORDER BY count DESC
    """
    return _rows_to_dicts(get_connection(), sql, params or None)
