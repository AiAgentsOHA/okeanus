"""FastAPI router for the ML intelligence layer."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from okeanus.db.postgres import get_session
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


@router.post("/correlations/granger")
async def granger_causality(code_a: str, code_b: str, max_lag: int = 14) -> dict[str, Any]:
    async with get_session() as session:
        results = await orchestrator.run_granger_test(session, code_a, code_b, max_lag=max_lag)
    return {"code_a": code_a, "code_b": code_b, "count": len(results), "results": results}


@router.get("/correlations/pairs")
async def discover_pairs(min_points: int = 30, max_pairs: int = 200) -> dict[str, Any]:
    async with get_session() as session:
        pairs = await orchestrator.discover_pairs(session, min_points=min_points, max_pairs=max_pairs)
    return {"count": len(pairs), "pairs": pairs}


@router.post("/graph/backfill")
async def run_backfill(run_correlations: bool = True) -> dict[str, Any]:
    async with get_session() as session:
        counts = await orchestrator.run_backfill(session, run_correlations=run_correlations)
    return {"status": "complete", "edges_created": counts}


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


# -- Feedback loop endpoints --


@router.post("/feedback")
async def submit_feedback(
    insight_id: str,
    feedback_type: str,
    user_score: float | None = None,
    notes: str | None = None,
    outcome_observed: str | None = None,
) -> dict[str, Any]:
    async with get_session() as session:
        result = await orchestrator.submit_feedback(
            session, insight_id, feedback_type,
            user_score=user_score, notes=notes,
            outcome_observed=outcome_observed,
        )
        await session.commit()
    return result


@router.get("/calibration")
async def calibration_report(bucket_count: int = 5) -> dict[str, Any]:
    async with get_session() as session:
        return await orchestrator.get_calibration(session, bucket_count=bucket_count)


# -- Entity resolution endpoints --


@router.get("/entities/duplicates")
async def find_duplicates(entity_type: str | None = None, limit: int = 100) -> dict[str, Any]:
    async with get_session() as session:
        dupes = await orchestrator.find_duplicate_entities(session, entity_type=entity_type, limit=limit)
    return {"count": len(dupes), "duplicates": dupes}


@router.post("/entities/merge")
async def merge_entities(keep_id: str, merge_id: str) -> dict[str, Any]:
    async with get_session() as session:
        result = await orchestrator.merge_entities(session, keep_id, merge_id)
        await session.commit()
    return result


@router.post("/entities/auto-resolve")
async def auto_resolve(
    entity_type: str | None = None,
    min_confidence: float = 0.95,
    dry_run: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    async with get_session() as session:
        result = await orchestrator.auto_resolve_entities(
            session, entity_type=entity_type,
            min_confidence=min_confidence, dry_run=dry_run, limit=limit,
        )
        if not dry_run:
            await session.commit()
    return result
