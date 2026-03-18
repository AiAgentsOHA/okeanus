"""FastAPI router for the ML intelligence layer."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from okeanus.db.session import get_session
from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator

router = APIRouter(prefix="/ml/intelligence", tags=["ml-intelligence"])
orchestrator = IntelligenceOrchestrator()


@router.post("/search")
async def semantic_search(query: str, limit: int = 10, source_type: str | None = None) -> dict[str, Any]:
    async with get_session() as session:
        results = await orchestrator.semantic_search(session, query, limit=limit, source_type=source_type)
    return {"query": query, "count": len(results), "results": results}


@router.get("/graph/{node_id}")
async def graph_neighbors(node_id: str, depth: int = 2) -> dict[str, Any]:
    async with get_session() as session:
        return await orchestrator.graph_query(session, node_id, depth=depth)


@router.get("/bridges")
async def bridge_concepts(top_k: int = 20) -> dict[str, Any]:
    async with get_session() as session:
        bridges = await orchestrator.find_bridge_concepts(session, top_k=top_k)
    return {"count": len(bridges), "bridges": bridges}


@router.get("/insights")
async def list_insights(status: str | None = None, limit: int = 50) -> dict[str, Any]:
    async with get_session() as session:
        insights = await orchestrator.get_insights(session, status=status, limit=limit)
    return {"count": len(insights), "insights": insights}


@router.post("/hypothesis")
async def generate_hypothesis(topic: str, evidence: str = "", domains: str = "") -> dict[str, Any]:
    domain_list = [d.strip() for d in domains.split(",") if d.strip()] if domains else None
    async with get_session() as session:
        return await orchestrator.generate_hypothesis(session, topic, evidence, domain_list)


@router.post("/correlations/scan")
async def run_correlation_scan() -> dict[str, Any]:
    async with get_session() as session:
        results = await orchestrator.run_correlation_scan(session)
    return {"count": len(results), "correlations": results}


@router.get("/graph/stats")
async def graph_stats() -> dict[str, Any]:
    try:
        from okeanus.ml.graph.algorithms import GraphAlgorithms
        algos = GraphAlgorithms()
        async with get_session() as session:
            return await algos.graph_summary(session)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/graph/communities")
async def graph_communities(domain: str | None = None) -> dict[str, Any]:
    try:
        from okeanus.ml.graph.algorithms import GraphAlgorithms
        algos = GraphAlgorithms()
        async with get_session() as session:
            communities = await algos.detect_communities(session, domain=domain)
        return {"count": len(communities), "communities": communities}
    except Exception as exc:
        return {"error": str(exc)}
