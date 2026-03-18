"""Analytics endpoints backed by DuckDB for fast OLAP queries."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from functools import partial
from typing import Annotated, Any

from fastapi import APIRouter, Query

from okeanus.db import duckdb as duck

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Helper -- run a sync DuckDB function in the default thread-pool executor
# ---------------------------------------------------------------------------

async def _run(func, *args, **kwargs) -> Any:  # noqa: ANN401
    """Run a synchronous callable in an executor to avoid blocking the loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


# ===================================================================
# Sync
# ===================================================================


@router.post("/sync")
async def sync() -> dict[str, Any]:
    """Sync all economy tables from PostgreSQL into local DuckDB tables."""
    counts = await _run(duck.sync_from_postgres)
    return {"status": "ok", "tables": counts}


# ===================================================================
# TimeSeries
# ===================================================================


@router.get("/timeseries/rollup")
async def timeseries_rollup(
    code: Annotated[str | None, Query(description="Series code")] = None,
    commodity: Annotated[str | None, Query(description="Commodity filter")] = None,
    country: Annotated[str | None, Query(description="Country ISO code")] = None,
    source_name: Annotated[str | None, Query(description="Data source name")] = None,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
    aggregation: Annotated[str, Query(description="Aggregation: daily, weekly, monthly, yearly")] = "monthly",
) -> list[dict[str, Any]]:
    """Aggregate time series data (rollup)."""
    return await _run(
        duck.ts_rollup,
        code=code,
        commodity=commodity,
        country=country,
        source_name=source_name,
        time_start=time_start,
        time_end=time_end,
        aggregation=aggregation,
    )


@router.get("/timeseries/moving-average")
async def timeseries_moving_average(
    code: Annotated[str, Query(description="Series code")],
    window: Annotated[int, Query(ge=2, le=365, description="Window size")] = 7,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> list[dict[str, Any]]:
    """Rolling average and standard deviation."""
    return await _run(
        duck.ts_moving_average,
        code=code,
        window=window,
        time_start=time_start,
        time_end=time_end,
    )


@router.get("/timeseries/yoy-change")
async def timeseries_yoy_change(
    code: Annotated[str, Query(description="Series code")],
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> list[dict[str, Any]]:
    """Year-over-year percentage change."""
    return await _run(
        duck.ts_yoy_change,
        code=code,
        time_start=time_start,
        time_end=time_end,
    )


@router.get("/timeseries/volatility")
async def timeseries_volatility(
    code: Annotated[str, Query(description="Series code")],
    window: Annotated[int, Query(ge=2, le=365, description="Rolling window")] = 30,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> list[dict[str, Any]]:
    """Rolling volatility (stddev and percentage returns)."""
    return await _run(
        duck.ts_volatility,
        code=code,
        window=window,
        time_start=time_start,
        time_end=time_end,
    )


@router.get("/timeseries/correlation")
async def timeseries_correlation(
    code_a: Annotated[str, Query(description="First series code")],
    code_b: Annotated[str, Query(description="Second series code")],
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> list[dict[str, Any]]:
    """Pearson correlation between two time series."""
    return await _run(
        duck.ts_correlation,
        code_a=code_a,
        code_b=code_b,
        time_start=time_start,
        time_end=time_end,
    )


@router.get("/timeseries/trend")
async def timeseries_trend(
    code: Annotated[str, Query(description="Series code")],
    window: Annotated[int, Query(ge=2, le=60, description="Trend window")] = 12,
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> list[dict[str, Any]]:
    """Centered moving average trend decomposition."""
    return await _run(
        duck.ts_trend,
        code=code,
        window=window,
        time_start=time_start,
        time_end=time_end,
    )


# ===================================================================
# Entities
# ===================================================================


@router.get("/entities/distribution")
async def entities_distribution(
    group_by: Annotated[str, Query(description="Group by: entity_type, country, sector")] = "entity_type",
) -> list[dict[str, Any]]:
    """Count entities by a grouping column."""
    return await _run(duck.entity_distribution, group_by=group_by)


@router.get("/entities/connectivity")
async def entities_connectivity() -> list[dict[str, Any]]:
    """Degree centrality (in + out edges) for every entity."""
    return await _run(duck.entity_connectivity)


@router.get("/entities/density")
async def entities_density(
    resolution: Annotated[float, Query(ge=0.01, le=10.0, description="Lat/lon bin size in degrees")] = 1.0,
) -> list[dict[str, Any]]:
    """Geographic density grid for entities."""
    return await _run(duck.entity_density, resolution=resolution)


# ===================================================================
# Flows
# ===================================================================


@router.get("/flows/trade-balance")
async def flows_trade_balance(
    time_start: Annotated[datetime | None, Query(description="Start time (ISO 8601)")] = None,
    time_end: Annotated[datetime | None, Query(description="End time (ISO 8601)")] = None,
) -> list[dict[str, Any]]:
    """Net trade by country pair."""
    return await _run(
        duck.flow_trade_balance,
        time_start=time_start,
        time_end=time_end,
    )


@router.get("/flows/top")
async def flows_top(
    n: Annotated[int, Query(ge=1, le=500, description="Number of top flows")] = 20,
    flow_type: Annotated[str | None, Query(description="Flow type filter")] = None,
) -> list[dict[str, Any]]:
    """Top flows by amount for Sankey diagrams."""
    return await _run(duck.flow_top_n, n=n, flow_type=flow_type)


@router.get("/flows/network")
async def flows_network() -> list[dict[str, Any]]:
    """Network summary statistics."""
    return await _run(duck.flow_network_stats)


# ===================================================================
# Events
# ===================================================================


@router.get("/events/frequency")
async def events_frequency(
    aggregation: Annotated[str, Query(description="Aggregation: daily, weekly, monthly, yearly")] = "monthly",
    event_type: Annotated[str | None, Query(description="Event type filter")] = None,
) -> list[dict[str, Any]]:
    """Event frequency histogram by type and period."""
    return await _run(
        duck.event_frequency,
        aggregation=aggregation,
        event_type=event_type,
    )


@router.get("/events/severity-trend")
async def events_severity_trend(
    aggregation: Annotated[str, Query(description="Aggregation: daily, weekly, monthly, yearly")] = "monthly",
) -> list[dict[str, Any]]:
    """Severity percentiles over time."""
    return await _run(duck.event_severity_trend, aggregation=aggregation)


@router.get("/events/correlation")
async def events_correlation(
    ts_code: Annotated[str, Query(description="Time series code to correlate with events")],
    aggregation: Annotated[str, Query(description="Aggregation: daily, weekly, monthly, yearly")] = "monthly",
) -> list[dict[str, Any]]:
    """Correlate event counts with a time series."""
    return await _run(
        duck.event_economic_correlation,
        ts_code=ts_code,
        aggregation=aggregation,
    )


# ===================================================================
# Assessments
# ===================================================================


@router.get("/assessments/distribution")
async def assessments_distribution(
    metric_code: Annotated[str, Query(description="Metric code")],
) -> list[dict[str, Any]]:
    """Score distribution statistics for a metric."""
    return await _run(duck.assessment_distribution, metric_code=metric_code)


@router.get("/assessments/ranking")
async def assessments_ranking(
    metric_code: Annotated[str, Query(description="Metric code")],
    limit: Annotated[int, Query(ge=1, le=500, description="Max results")] = 50,
) -> list[dict[str, Any]]:
    """Entity ranking by assessment score."""
    return await _run(
        duck.assessment_ranking,
        metric_code=metric_code,
        limit=limit,
    )


@router.get("/assessments/trend")
async def assessments_trend(
    metric_code: Annotated[str, Query(description="Metric code")],
    entity_id: Annotated[str | None, Query(description="Entity UUID")] = None,
) -> list[dict[str, Any]]:
    """Assessment score over time."""
    return await _run(
        duck.assessment_trend,
        metric_code=metric_code,
        entity_id=entity_id,
    )


@router.get("/assessments/compare")
async def assessments_compare(
    entity_id: Annotated[str, Query(description="Entity UUID")],
) -> list[dict[str, Any]]:
    """Cross-compare all assessor scores for one entity."""
    return await _run(duck.assessment_cross_compare, entity_id=entity_id)


# ===================================================================
# Claims
# ===================================================================


@router.get("/claims/delivery")
async def claims_delivery() -> list[dict[str, Any]]:
    """Completion rates by status."""
    return await _run(duck.claim_delivery_stats)


@router.get("/claims/deadlines")
async def claims_deadlines() -> list[dict[str, Any]]:
    """Deadline analysis with overdue counts."""
    return await _run(duck.claim_deadline_analysis)


@router.get("/claims/gaps")
async def claims_gaps() -> list[dict[str, Any]]:
    """Target value vs progress gap analysis."""
    return await _run(duck.claim_gap_analysis)


# ===================================================================
# Relationships
# ===================================================================


@router.get("/relationships/centrality")
async def relationships_centrality(
    limit: Annotated[int, Query(ge=1, le=500, description="Max results")] = 50,
) -> list[dict[str, Any]]:
    """Degree centrality from the relationships table."""
    return await _run(duck.relationship_degree_centrality, limit=limit)


@router.get("/relationships/components")
async def relationships_components() -> list[dict[str, Any]]:
    """Connected components via recursive CTE."""
    return await _run(duck.relationship_components)


@router.get("/relationships/types")
async def relationships_types() -> list[dict[str, Any]]:
    """Relationship type distribution."""
    return await _run(duck.relationship_type_distribution)


# ===================================================================
# Observations
# ===================================================================


@router.get("/observations/temporal")
async def observations_temporal(
    aggregation: Annotated[str, Query(description="Aggregation: daily, weekly, monthly, yearly")] = "daily",
    obs_type: Annotated[str | None, Query(description="Observation type filter")] = None,
) -> list[dict[str, Any]]:
    """Observation counts by period and type."""
    return await _run(
        duck.observation_temporal,
        aggregation=aggregation,
        obs_type=obs_type,
    )


@router.get("/observations/spatial-grid")
async def observations_spatial_grid(
    resolution: Annotated[float, Query(ge=0.01, le=10.0, description="Lat/lon bin size in degrees")] = 1.0,
    obs_type: Annotated[str | None, Query(description="Observation type filter")] = None,
) -> list[dict[str, Any]]:
    """Spatial heatmap grid of observations."""
    return await _run(
        duck.observation_spatial_grid,
        resolution=resolution,
        obs_type=obs_type,
    )


@router.get("/observations/sources")
async def observations_sources() -> list[dict[str, Any]]:
    """Records per source with time range coverage."""
    return await _run(duck.observation_source_coverage)


# ===================================================================
# Export
# ===================================================================


@router.post("/export")
async def export_parquet(
    sql: Annotated[str, Query(description="DuckDB SQL query to export")],
    output_path: Annotated[str, Query(description="Output Parquet file path")] = "./data/export.parquet",
) -> dict[str, Any]:
    """Export a query result to a Parquet file."""
    result_path = await _run(duck.export_to_parquet, sql, output_path)
    return {"status": "ok", "path": str(result_path)}
