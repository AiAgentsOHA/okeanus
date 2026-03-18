"""Intelligence layer orchestrator — coordinates graph, vectors, correlation, reasoning."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """Central coordinator for the ML intelligence pipeline."""

    async def on_data_ingested(
        self,
        session: AsyncSession,
        source_name: str,
        record_count: int,
        items: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Hook called after data ingestion to update intelligence layers."""
        results: dict[str, Any] = {"source": source_name, "records": record_count}

        # Index new items into embeddings
        if items:
            try:
                from okeanus.ml.vectors.indexer import EmbeddingIndexer
                indexer = EmbeddingIndexer()
                embedded = await indexer.index_new_items(
                    session, items, source_type="entity", source_table="entities"
                )
                results["embedded"] = embedded
            except Exception as exc:
                logger.debug("Embedding indexer not available: %s", exc)

        return results

    async def semantic_search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search across all embedded data."""
        from okeanus.ml.vectors.search import VectorSearch
        searcher = VectorSearch()
        return await searcher.search(session, query, limit=limit, source_type=source_type)

    async def graph_query(
        self,
        session: AsyncSession,
        node_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Query the knowledge graph for neighbors of a node."""
        from uuid import UUID
        from okeanus.ml.graph.query import GraphQueryEngine
        engine = GraphQueryEngine()
        return await engine.get_neighbors(session, UUID(node_id), depth=depth)

    async def find_bridge_concepts(
        self,
        session: AsyncSession,
        top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Find bridge concepts using graph algorithms."""
        from okeanus.ml.graph.algorithms import GraphAlgorithms
        algos = GraphAlgorithms()
        return await algos.cross_domain_bridges(session, top_k=top_k)

    async def get_insights(
        self,
        session: AsyncSession,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get materialized insights."""
        from okeanus.ml.synthesis.insights import InsightManager
        mgr = InsightManager()
        insights = await mgr.get_insights(session, status=status, limit=limit)
        return [
            {
                "id": str(i.id),
                "type": i.insight_type,
                "title": i.title,
                "description": i.description[:500],
                "confidence": i.confidence,
                "classification": i.classification,
                "status": i.status,
                "domains": i.involved_domains,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in insights
        ]

    async def generate_hypothesis(
        self,
        session: AsyncSession,
        topic: str,
        evidence: str,
        domains: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a novel hypothesis using UoT thought graph + PRefLexOR convergence.

        Pipeline: UoT (thought graph with KG integration) -> PRefLexOR (convergence loop)
        """
        from okeanus.ml.synthesis.uot import UniverseOfThoughts
        from okeanus.ml.synthesis.preflex import PRefLexOR

        uot = UniverseOfThoughts()
        preflex = PRefLexOR()

        # Step 1: UoT creative reasoning with thought graph + KG integration
        creative = await uot.full_creative_reasoning(
            topic, evidence,
            domains or ["marine_biology", "economics", "climate"],
            session=session,
        )

        # Step 2: Build rich evidence from thought graph for PRefLexOR
        top_thoughts = creative.get("top_thoughts", [])
        thought_summary = "\n".join(
            f"- [{t.get('type', '?')}] (score={t.get('score', 0):.2f}) "
            f"{t.get('content', '')[:200]}"
            for t in top_thoughts[:10]
        )

        combined_evidence = (
            f"Topic: {topic}\n"
            f"Original evidence: {evidence}\n\n"
            f"Top thoughts from UoT thought graph "
            f"({creative.get('thought_graph', {}).get('thought_count', 0)} total, "
            f"after pruning):\n{thought_summary}\n\n"
            f"Depth stats: {creative.get('depth_stats', [])}\n"
        )

        # Step 3: PRefLexOR convergence loop
        refined = await preflex.run_pipeline(combined_evidence, session=session)

        return {
            "topic": topic,
            "creative_reasoning": creative,
            "refined_analysis": refined.get("findings", []),
            "convergence": {
                "converged": refined.get("converged", False),
                "cycles_run": refined.get("cycles_run", 0),
                "score_history": refined.get("score_history", []),
            },
            "final_scores": refined.get("final_scores", {}),
            "meta": refined.get("meta", {}),
        }

    async def run_correlation_scan(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Run a full correlation scan across all data.

        Uses the enhanced correlator with auto-discovery, lag sweep,
        and anomaly clustering.
        """
        from okeanus.ml.synthesis.correlator import CorrelationEngine
        engine = CorrelationEngine()
        return await engine.full_scan(session)

    async def run_granger_test(
        self,
        session: AsyncSession,
        code_a: str,
        code_b: str,
        max_lag: int = 14,
    ) -> list[dict[str, Any]]:
        """Test Granger causality between two time series."""
        from okeanus.ml.synthesis.correlator import CorrelationEngine
        engine = CorrelationEngine()
        return await engine.granger_causality(session, code_a, code_b, max_lag=max_lag)

    async def discover_pairs(
        self,
        session: AsyncSession,
        min_points: int = 30,
        max_pairs: int = 200,
    ) -> list[dict[str, Any]]:
        """Auto-discover time series pairs worth testing for correlations."""
        from okeanus.ml.synthesis.correlator import CorrelationEngine
        engine = CorrelationEngine()
        return await engine.auto_discover_pairs(session, min_points=min_points, max_pairs=max_pairs)

    async def run_backfill(
        self,
        session: AsyncSession,
        run_correlations: bool = True,
    ) -> dict[str, int]:
        """Run the full knowledge graph backfill pipeline."""
        from okeanus.ml.graph.builder import KnowledgeGraphBuilder
        builder = KnowledgeGraphBuilder()
        return await builder.backfill_all(session, run_correlations=run_correlations)

    # -- Feedback loop --

    async def submit_feedback(
        self,
        session: AsyncSession,
        insight_id: str,
        feedback_type: str,
        user_score: float | None = None,
        notes: str | None = None,
        outcome_observed: str | None = None,
    ) -> dict[str, Any]:
        """Submit user feedback on an insight."""
        from uuid import UUID
        from okeanus.ml.synthesis.insights import InsightManager
        mgr = InsightManager()
        fb = await mgr.submit_feedback(
            session, UUID(insight_id), feedback_type,
            user_score=user_score, notes=notes,
            outcome_observed=outcome_observed,
        )
        return {
            "id": str(fb.id),
            "insight_id": str(fb.insight_id),
            "feedback_type": fb.feedback_type,
            "user_score": fb.user_score,
        }

    async def get_calibration(
        self,
        session: AsyncSession,
        bucket_count: int = 5,
    ) -> dict[str, Any]:
        """Get calibration report: predicted confidence vs actual outcomes."""
        from okeanus.ml.synthesis.insights import InsightManager
        mgr = InsightManager()
        return await mgr.calibration_report(session, bucket_count=bucket_count)

    # -- Entity resolution --

    async def find_duplicate_entities(
        self,
        session: AsyncSession,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find candidate duplicate entities across sources."""
        from okeanus.ml.synthesis.entity_resolution import EntityResolver
        resolver = EntityResolver()
        return await resolver.find_duplicates(session, entity_type=entity_type, limit=limit)

    async def merge_entities(
        self,
        session: AsyncSession,
        keep_id: str,
        merge_id: str,
    ) -> dict[str, Any]:
        """Merge two entities: keep one, redirect references from the other."""
        from uuid import UUID
        from okeanus.ml.synthesis.entity_resolution import EntityResolver
        resolver = EntityResolver()
        return await resolver.merge_entities(session, UUID(keep_id), UUID(merge_id))

    async def auto_resolve_entities(
        self,
        session: AsyncSession,
        entity_type: str | None = None,
        min_confidence: float = 0.95,
        dry_run: bool = True,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Auto-resolve high-confidence duplicate entities."""
        from okeanus.ml.synthesis.entity_resolution import EntityResolver
        resolver = EntityResolver()
        return await resolver.auto_resolve(
            session, entity_type=entity_type,
            min_confidence=min_confidence, dry_run=dry_run, limit=limit,
        )
