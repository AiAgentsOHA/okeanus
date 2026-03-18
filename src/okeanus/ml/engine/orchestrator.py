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
        """Generate a novel hypothesis using UoT + PRefLexOR."""
        from okeanus.ml.synthesis.uot import UniverseOfThoughts
        from okeanus.ml.synthesis.preflex import PRefLexOR

        uot = UniverseOfThoughts()
        preflex = PRefLexOR()

        # Step 1: UoT creative reasoning
        creative = await uot.full_creative_reasoning(
            topic, evidence, domains or ["marine_biology", "economics", "climate"]
        )

        # Step 2: PRefLexOR critique
        combined_evidence = (
            f"Topic: {topic}\n"
            f"Evidence: {evidence}\n"
            f"Cross-domain analogies: {len(creative.get('analogies', []))}\n"
            f"Expansion directions: {len(creative.get('expansions', []))}\n"
            f"Assumption challenges: {len(creative.get('transformations', []))}\n"
        )
        refined = await preflex.run_pipeline(combined_evidence, session=session)

        return {
            "topic": topic,
            "creative_reasoning": creative,
            "refined_analysis": refined.get("findings", []),
            "meta": refined.get("meta", {}),
        }

    async def run_correlation_scan(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Run a full correlation scan across all data."""
        from okeanus.ml.synthesis.correlator import CorrelationEngine
        engine = CorrelationEngine()
        return await engine.full_scan(session)
