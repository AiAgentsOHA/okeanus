"""Run the full ML intelligence pipeline: embed → backfill → hypothesis."""

import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    from okeanus.db.postgres import get_session
    from okeanus.ml.vectors.indexer import EmbeddingIndexer
    from okeanus.ml.engine.orchestrator import IntelligenceOrchestrator

    indexer = EmbeddingIndexer()
    orch = IntelligenceOrchestrator()

    # Step 1: Embed all entities + events + observations
    logger.info("=== Step 1: Building embeddings (entities, events, observations) ===")
    async with get_session() as session:
        counts = await indexer.build_full_index(session)
        await session.commit()
    logger.info("Embedded: %s", counts)

    # Step 1b: Sync Postgres tables into DuckDB for analytics queries
    logger.info("=== Step 1b: Syncing DuckDB from Postgres ===")
    from okeanus.db.duckdb import sync_from_postgres
    sync_counts = sync_from_postgres()
    logger.info("DuckDB sync: %s", sync_counts)

    # Step 2: Graph backfill (spatial + semantic + correlation edges)
    logger.info("=== Step 2: Graph backfill ===")
    async with get_session() as session:
        edge_counts = await orch.run_backfill(session, run_correlations=True)
        await session.commit()
    logger.info("Edges created: %s", edge_counts)

    # Step 3: Generate hypothesis
    logger.info("=== Step 3: Generating hypothesis ===")
    async with get_session() as session:
        result = await orch.generate_hypothesis(
            session,
            topic="marine biodiversity and ocean temperature patterns",
            evidence="1221 entities, 900 events, 65000+ observations (all embedded); 2696 time series; 119 data sources; 10000+ knowledge edges",
            domains=["marine_biology", "climate", "geology"],
        )
    logger.info("Hypothesis generated with %d top thoughts", len(result.get("top_thoughts", [])))

    # Step 4: Stats
    logger.info("=== Step 4: Verification ===")
    async with get_session() as session:
        stats = await indexer.embedding_stats(session)
    logger.info("Embedding stats: %s", stats)
    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    asyncio.run(main())
