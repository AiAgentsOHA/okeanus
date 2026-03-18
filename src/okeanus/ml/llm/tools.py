"""Tool definitions for Claude tool-use -- mapped to Okeanus API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from okeanus.db.postgres import get_session

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "query_timeseries",
        "description": "Query time series economic data (prices, indices, indicators). Returns paginated results with code, value, timestamp, commodity, country.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Series code (e.g., 'FISH_INDEX', 'nfip-claims')"},
                "commodity": {"type": "string", "description": "Commodity filter (e.g., 'salmon', 'crude_oil')"},
                "country": {"type": "string", "description": "Country ISO code (e.g., 'US', 'NO')"},
                "source_name": {"type": "string", "description": "Data source name (e.g., 'FRED', 'SSB Norway')"},
                "time_start": {"type": "string", "description": "Start time ISO 8601"},
                "time_end": {"type": "string", "description": "End time ISO 8601"},
                "limit": {"type": "integer", "description": "Max results (default 100)"},
            },
        },
    },
    {
        "name": "query_entities",
        "description": "Query economic entities (organizations, ports, MPAs, fisheries, countries, projects). Filter by type, name, country, sector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "description": "Entity type (company, country, port, mpa, fish_stock, infrastructure, project, contract, ecosystem)"},
                "name": {"type": "string", "description": "Name search (partial match)"},
                "country": {"type": "string", "description": "Country ISO code"},
                "sector": {"type": "string", "description": "Sector filter"},
                "limit": {"type": "integer", "description": "Max results"},
            },
        },
    },
    {
        "name": "query_observations",
        "description": "Query ocean observations (physical, vessel, acoustic, biological, satellite). Returns GeoJSON FeatureCollection.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bbox": {"type": "string", "description": "Bounding box: west,south,east,north"},
                "obs_type": {"type": "string", "description": "Type: physical, vessel, acoustic, biological, satellite"},
                "time_start": {"type": "string", "description": "Start time ISO 8601"},
                "time_end": {"type": "string", "description": "End time ISO 8601"},
                "source_name": {"type": "string", "description": "Data source name"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "query_flows",
        "description": "Query economic flows (trade, aid, catch movements between entities). Filter by type, commodity, time range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "flow_type": {"type": "string", "description": "Flow type (fish_trade, development_aid, climate_finance, catch, export, import)"},
                "commodity": {"type": "string", "description": "Commodity filter"},
                "time_start": {"type": "string", "description": "Start time ISO 8601"},
                "time_end": {"type": "string", "description": "End time ISO 8601"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "query_events",
        "description": "Query economic events (floods, MPA designations, spills). Filter by type, location, time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {"type": "string", "description": "Event type (flood_claim, flood_policy, mpa_designation)"},
                "bbox": {"type": "string", "description": "Bounding box: west,south,east,north"},
                "time_start": {"type": "string", "description": "Start time ISO 8601"},
                "time_end": {"type": "string", "description": "End time ISO 8601"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_entity_context",
        "description": "Get full context for an entity: its assessments, flows, relationships, events, time series, and nearby observations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Entity UUID"},
                "include_observations": {"type": "boolean", "description": "Include nearby ocean observations (default false)"},
                "observation_radius_km": {"type": "number", "description": "Radius in km for nearby observations (default 50)"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "spatial_search",
        "description": "Unified spatial search across entities, observations, timeseries, and events within a bounding box.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bbox": {"type": "string", "description": "Bounding box: west,south,east,north"},
                "entity_types": {"type": "string", "description": "Comma-separated entity types to include"},
                "obs_types": {"type": "string", "description": "Comma-separated observation types"},
                "time_start": {"type": "string", "description": "Start time ISO 8601"},
                "time_end": {"type": "string", "description": "End time ISO 8601"},
            },
            "required": ["bbox"],
        },
    },
    {
        "name": "entity_network",
        "description": "Traverse the entity relationship/flow network from a starting entity. Returns nodes and edges for graph visualization.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Starting entity UUID"},
                "depth": {"type": "integer", "description": "Traversal depth 1-3 (default 1)"},
            },
            "required": ["entity_id"],
        },
    },
    {
        "name": "run_analytics",
        "description": "Run DuckDB analytics on the data. Supports rollups, moving averages, correlations, rankings, trade balances, and more.",
        "input_schema": {
            "type": "object",
            "properties": {
                "function": {
                    "type": "string",
                    "description": "Analytics function name",
                    "enum": [
                        "ts_rollup", "ts_moving_average", "ts_yoy_change", "ts_volatility",
                        "ts_correlation", "ts_trend", "entity_distribution", "entity_connectivity",
                        "flow_trade_balance", "flow_top_n", "event_frequency",
                        "assessment_distribution", "assessment_ranking",
                        "observation_temporal", "observation_source_coverage",
                    ],
                },
                "params": {
                    "type": "object",
                    "description": "Parameters for the analytics function (varies by function). Common: code, time_start, time_end, aggregation, limit.",
                },
            },
            "required": ["function"],
        },
    },
    {
        "name": "list_data_sources",
        "description": "List all available data sources with their names, descriptions, and update frequencies.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "query_assessments",
        "description": "Query assessments (ratings, scores, certifications for entities). Filter by assessor, metric, entity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assessor": {"type": "string", "description": "Assessor name (e.g., 'ICES', 'WBA', 'Verra')"},
                "metric_code": {"type": "string", "description": "Metric code (e.g., 'stock_status', 'iuu_overall')"},
                "entity_id": {"type": "string", "description": "Entity UUID"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "search_marine_regions",
        "description": "Search marine regions by name or MRGID. Returns boundaries and metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Region name to search"},
                "mrgid": {"type": "integer", "description": "Marine Regions Gazetteer ID"},
            },
        },
    },
    {
        "name": "semantic_search",
        "description": "Search for ocean data by meaning using AI embeddings. Finds semantically similar entities, events, and observations across all data sources. Use when the user asks about a topic and you want to find related data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                "source_type": {"type": "string", "description": "Filter by type: entity, event, observation", "enum": ["entity", "event", "observation"]},
            },
            "required": ["query"],
        },
    },
    {
        "name": "graph_query",
        "description": "Explore the knowledge graph to find relationships between entities. Returns neighbors, connections, and paths between nodes. Use when investigating how things are connected.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node_id": {"type": "string", "description": "UUID of the node to explore"},
                "depth": {"type": "integer", "description": "How many hops to traverse (default 2)", "default": 2},
            },
            "required": ["node_id"],
        },
    },
    {
        "name": "get_insights",
        "description": "Retrieve AI-generated insights about cross-domain patterns, correlations, and anomalies. These are pre-computed discoveries from the intelligence engine.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status", "enum": ["candidate", "validated", "rejected"]},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
            },
        },
    },
    {
        "name": "find_bridge_concepts",
        "description": "Discover bridge concepts — entities that connect different data domains. Uses graph algorithms to find nodes sitting between marine biology, economics, climate, and other domains.",
        "input_schema": {
            "type": "object",
            "properties": {
                "top_k": {"type": "integer", "description": "How many bridge concepts to return (default 10)", "default": 10},
            },
        },
    },
    {
        "name": "generate_hypothesis",
        "description": "Generate a novel scientific hypothesis about a topic using cross-domain reasoning, analogical transfer, and adversarial critique. Use for creative exploration of what the data means TOGETHER.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The topic or question to hypothesize about"},
                "evidence": {"type": "string", "description": "Supporting evidence or context"},
                "domains": {"type": "array", "items": {"type": "string"}, "description": "Domains to explore (e.g. ['marine_biology', 'economics'])"},
            },
            "required": ["topic"],
        },
    },
]


async def execute_tool(name: str, params: dict[str, Any]) -> Any:
    """Execute a tool by calling the corresponding internal API function."""
    dispatch = {
        "query_timeseries": _query_timeseries,
        "query_entities": _query_entities,
        "query_observations": _query_observations,
        "query_flows": _query_flows,
        "query_events": _query_events,
        "get_entity_context": _get_entity_context,
        "spatial_search": _spatial_search,
        "entity_network": _entity_network,
        "run_analytics": _run_analytics,
        "list_data_sources": _list_data_sources,
        "query_assessments": _query_assessments,
        "search_marine_regions": _search_marine_regions,
    }
    handler = dispatch.get(name)
    if handler is not None:
        return await handler(params)

    # Intelligence layer tools (lazy imports to avoid circular deps)
    if name == "semantic_search":
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator
        orch = IntelligenceOrchestrator()
        async with get_session() as session:
            return await orch.semantic_search(session, params["query"], limit=params.get("limit", 10), source_type=params.get("source_type"))

    elif name == "graph_query":
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator
        orch = IntelligenceOrchestrator()
        async with get_session() as session:
            return await orch.graph_query(session, params["node_id"], depth=params.get("depth", 2))

    elif name == "get_insights":
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator
        orch = IntelligenceOrchestrator()
        async with get_session() as session:
            return await orch.get_insights(session, status=params.get("status"), limit=params.get("limit", 20))

    elif name == "find_bridge_concepts":
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator
        orch = IntelligenceOrchestrator()
        async with get_session() as session:
            return await orch.find_bridge_concepts(session, top_k=params.get("top_k", 10))

    elif name == "generate_hypothesis":
        from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator
        orch = IntelligenceOrchestrator()
        async with get_session() as session:
            return await orch.generate_hypothesis(session, params["topic"], params.get("evidence", ""), params.get("domains"))

    return {"error": f"Unknown tool: {name}"}


async def _query_timeseries(params: dict) -> dict:
    """Execute timeseries query internally."""
    from datetime import datetime

    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import TimeSeries, TimeSeriesRead

    stmt = select(TimeSeries)
    if params.get("code"):
        stmt = stmt.where(TimeSeries.code == params["code"])
    if params.get("commodity"):
        stmt = stmt.where(TimeSeries.commodity == params["commodity"])
    if params.get("country"):
        stmt = stmt.where(TimeSeries.country == params["country"])
    if params.get("source_name"):
        stmt = stmt.where(TimeSeries.source_name == params["source_name"])
    if params.get("time_start"):
        stmt = stmt.where(TimeSeries.timestamp >= datetime.fromisoformat(params["time_start"]))
    if params.get("time_end"):
        stmt = stmt.where(TimeSeries.timestamp <= datetime.fromisoformat(params["time_end"]))

    limit = min(params.get("limit", 100), 200)
    stmt = stmt.order_by(TimeSeries.timestamp.desc()).limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [TimeSeriesRead.model_validate(r).model_dump(mode="json") for r in rows],
        "count": len(rows),
    }


async def _query_entities(params: dict) -> dict:
    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import Entity, EntityRead

    stmt = select(Entity)
    if params.get("entity_type"):
        stmt = stmt.where(Entity.entity_type == params["entity_type"])
    if params.get("name"):
        stmt = stmt.where(Entity.name.ilike(f"%{params['name']}%"))
    if params.get("country"):
        stmt = stmt.where(Entity.country == params["country"])
    if params.get("sector"):
        stmt = stmt.where(Entity.sector == params["sector"])

    limit = min(params.get("limit", 100), 200)
    stmt = stmt.limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [EntityRead.model_validate(r).model_dump(mode="json") for r in rows],
        "count": len(rows),
    }


async def _query_observations(params: dict) -> dict:
    from datetime import datetime

    from geoalchemy2.functions import ST_MakeEnvelope
    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.base import Observation, ObservationBase

    stmt = select(Observation)
    if params.get("bbox"):
        w, s, e, n = [float(x) for x in params["bbox"].split(",")]
        stmt = stmt.where(Observation.geometry.ST_Intersects(ST_MakeEnvelope(w, s, e, n, 4326)))
    if params.get("obs_type"):
        stmt = stmt.where(Observation.obs_type == params["obs_type"])
    if params.get("time_start"):
        stmt = stmt.where(Observation.timestamp >= datetime.fromisoformat(params["time_start"]))
    if params.get("time_end"):
        stmt = stmt.where(Observation.timestamp <= datetime.fromisoformat(params["time_end"]))
    if params.get("source_name"):
        stmt = stmt.where(Observation.source_name == params["source_name"])

    limit = min(params.get("limit", 50), 200)
    stmt = stmt.order_by(Observation.timestamp.desc()).limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    features = [
        ObservationBase.model_validate(r).to_feature().model_dump(mode="json") for r in rows
    ]
    return {"type": "FeatureCollection", "features": features, "count": len(features)}


async def _query_flows(params: dict) -> dict:
    from datetime import datetime

    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import Flow, FlowRead

    stmt = select(Flow)
    if params.get("flow_type"):
        stmt = stmt.where(Flow.flow_type == params["flow_type"])
    if params.get("commodity"):
        stmt = stmt.where(Flow.commodity == params["commodity"])
    if params.get("time_start"):
        stmt = stmt.where(Flow.timestamp >= datetime.fromisoformat(params["time_start"]))
    if params.get("time_end"):
        stmt = stmt.where(Flow.timestamp <= datetime.fromisoformat(params["time_end"]))

    limit = min(params.get("limit", 100), 200)
    stmt = stmt.limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [FlowRead.model_validate(r).model_dump(mode="json") for r in rows],
        "count": len(rows),
    }


async def _query_events(params: dict) -> dict:
    from datetime import datetime

    from geoalchemy2.functions import ST_MakeEnvelope
    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import Event, EventRead

    stmt = select(Event)
    if params.get("event_type"):
        stmt = stmt.where(Event.event_type == params["event_type"])
    if params.get("bbox"):
        w, s, e, n = [float(x) for x in params["bbox"].split(",")]
        stmt = stmt.where(Event.geometry.ST_Intersects(ST_MakeEnvelope(w, s, e, n, 4326)))
    if params.get("time_start"):
        stmt = stmt.where(Event.timestamp >= datetime.fromisoformat(params["time_start"]))
    if params.get("time_end"):
        stmt = stmt.where(Event.timestamp <= datetime.fromisoformat(params["time_end"]))

    limit = min(params.get("limit", 100), 200)
    stmt = stmt.order_by(Event.timestamp.desc()).limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [EventRead.model_validate(r).model_dump(mode="json") for r in rows],
        "count": len(rows),
    }


async def _get_entity_context(params: dict) -> dict:
    """Internally call the entity-context endpoint logic."""
    import uuid as uuid_mod

    from sqlalchemy import or_, select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import (
        Assessment,
        AssessmentRead,
        Entity,
        EntityRead,
        Flow,
        FlowRead,
        Relationship,
        RelationshipRead,
    )

    entity_id = uuid_mod.UUID(params["entity_id"])

    async with async_session_factory() as session:
        entity = (
            await session.execute(select(Entity).where(Entity.id == entity_id))
        ).scalar_one_or_none()
        if not entity:
            return {"error": "Entity not found"}

        assessments = (
            await session.execute(
                select(Assessment).where(Assessment.entity_id == entity_id)
            )
        ).scalars().all()

        flows = (
            await session.execute(
                select(Flow).where(
                    or_(Flow.source_entity_id == entity_id, Flow.dest_entity_id == entity_id)
                )
            )
        ).scalars().all()

        relationships = (
            await session.execute(
                select(Relationship).where(
                    or_(
                        Relationship.source_entity_id == entity_id,
                        Relationship.dest_entity_id == entity_id,
                    )
                )
            )
        ).scalars().all()

    return {
        "entity": EntityRead.model_validate(entity).model_dump(mode="json"),
        "assessments": [
            AssessmentRead.model_validate(a).model_dump(mode="json") for a in assessments
        ],
        "flows": [FlowRead.model_validate(f).model_dump(mode="json") for f in flows],
        "relationships": [
            RelationshipRead.model_validate(r).model_dump(mode="json") for r in relationships
        ],
    }


async def _spatial_search(params: dict) -> dict:
    from geoalchemy2.functions import ST_MakeEnvelope
    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.base import Observation, ObservationBase
    from okeanus.schema.economy import Entity, EntityRead

    w, s, e, n = [float(x) for x in params["bbox"].split(",")]
    envelope = ST_MakeEnvelope(w, s, e, n, 4326)

    async with async_session_factory() as session:
        # Entities
        e_stmt = select(Entity).where(Entity.geometry.ST_Intersects(envelope)).limit(100)
        entities = (await session.execute(e_stmt)).scalars().all()

        # Observations
        o_stmt = select(Observation).where(
            Observation.geometry.ST_Intersects(envelope)
        ).limit(100)
        if params.get("obs_types"):
            types = params["obs_types"].split(",")
            o_stmt = o_stmt.where(Observation.obs_type.in_(types))
        observations = (await session.execute(o_stmt)).scalars().all()

    return {
        "entities": [EntityRead.model_validate(e).model_dump(mode="json") for e in entities],
        "observations": [
            ObservationBase.model_validate(o).to_feature().model_dump(mode="json")
            for o in observations
        ],
    }


async def _entity_network(params: dict) -> dict:
    import uuid as uuid_mod

    from sqlalchemy import or_, select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import (
        Entity,
        EntityRead,
        Flow,
        FlowRead,
        Relationship,
        RelationshipRead,
    )

    entity_id = uuid_mod.UUID(params["entity_id"])
    depth = min(params.get("depth", 1), 3)

    visited: set[uuid_mod.UUID] = {entity_id}
    frontier: set[uuid_mod.UUID] = {entity_id}
    all_rels: list = []
    all_flows: list = []

    async with async_session_factory() as session:
        for _ in range(depth):
            if not frontier:
                break
            frontier_list = list(frontier)

            rels = (
                await session.execute(
                    select(Relationship).where(
                        or_(
                            Relationship.source_entity_id.in_(frontier_list),
                            Relationship.dest_entity_id.in_(frontier_list),
                        )
                    )
                )
            ).scalars().all()
            all_rels.extend(rels)

            flows = (
                await session.execute(
                    select(Flow).where(
                        or_(
                            Flow.source_entity_id.in_(frontier_list),
                            Flow.dest_entity_id.in_(frontier_list),
                        )
                    ).limit(200)
                )
            ).scalars().all()
            all_flows.extend(flows)

            next_frontier: set[uuid_mod.UUID] = set()
            for r in rels:
                for eid in (r.source_entity_id, r.dest_entity_id):
                    if eid and eid not in visited:
                        next_frontier.add(eid)
                        visited.add(eid)
            for f in flows:
                for eid in (f.source_entity_id, f.dest_entity_id):
                    if eid and eid not in visited:
                        next_frontier.add(eid)
                        visited.add(eid)
            frontier = next_frontier

        # Fetch all entities
        entities = (
            await session.execute(select(Entity).where(Entity.id.in_(list(visited))))
        ).scalars().all()

    return {
        "nodes": [EntityRead.model_validate(e).model_dump(mode="json") for e in entities],
        "edges": (
            [RelationshipRead.model_validate(r).model_dump(mode="json") for r in all_rels]
            + [FlowRead.model_validate(f).model_dump(mode="json") for f in all_flows]
        ),
    }


async def _run_analytics(params: dict) -> dict:
    import asyncio
    from functools import partial

    from okeanus.db import duckdb

    func_name = params.get("function", "")
    func_params = params.get("params", {})

    func_map = {
        "ts_rollup": duckdb.ts_rollup,
        "ts_moving_average": duckdb.ts_moving_average,
        "ts_yoy_change": duckdb.ts_yoy_change,
        "ts_volatility": duckdb.ts_volatility,
        "ts_correlation": duckdb.ts_correlation,
        "ts_trend": duckdb.ts_trend,
        "entity_distribution": duckdb.entity_distribution,
        "entity_connectivity": duckdb.entity_connectivity,
        "flow_trade_balance": duckdb.flow_trade_balance,
        "flow_top_n": duckdb.flow_top_n,
        "event_frequency": duckdb.event_frequency,
        "assessment_distribution": duckdb.assessment_distribution,
        "assessment_ranking": duckdb.assessment_ranking,
        "observation_temporal": duckdb.observation_temporal,
        "observation_source_coverage": duckdb.observation_source_coverage,
    }

    func = func_map.get(func_name)
    if not func:
        return {
            "error": f"Unknown analytics function: {func_name}. "
            f"Available: {list(func_map.keys())}",
        }

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, partial(func, **func_params))
    return {"function": func_name, "results": result, "count": len(result)}


async def _list_data_sources(params: dict) -> dict:
    from okeanus.adapters import ADAPTER_REGISTRY

    sources = []
    for name, cls in ADAPTER_REGISTRY.items():
        adapter = cls()
        sources.append({
            "name": name,
            "description": cls.__doc__.split("\n")[0] if cls.__doc__ else "",
            "update_frequency": adapter.update_frequency,
        })
    return {"sources": sources, "total": len(sources)}


async def _query_assessments(params: dict) -> dict:
    import uuid as uuid_mod

    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.economy import Assessment, AssessmentRead

    stmt = select(Assessment)
    if params.get("assessor"):
        stmt = stmt.where(Assessment.assessor == params["assessor"])
    if params.get("metric_code"):
        stmt = stmt.where(Assessment.metric_code == params["metric_code"])
    if params.get("entity_id"):
        stmt = stmt.where(Assessment.entity_id == uuid_mod.UUID(params["entity_id"]))

    limit = min(params.get("limit", 100), 200)
    stmt = stmt.limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "items": [AssessmentRead.model_validate(r).model_dump(mode="json") for r in rows],
        "count": len(rows),
    }


async def _search_marine_regions(params: dict) -> dict:
    from sqlalchemy import select

    from okeanus.db.postgres import async_session_factory
    from okeanus.schema.base import Observation, ObservationBase

    stmt = select(Observation).where(Observation.obs_type == "economic")
    if params.get("name"):
        stmt = stmt.where(Observation.source_name.ilike(f"%{params['name']}%"))
    stmt = stmt.limit(50)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).scalars().all()

    return {
        "regions": [
            ObservationBase.model_validate(r).to_feature().model_dump(mode="json") for r in rows
        ],
        "count": len(rows),
    }
