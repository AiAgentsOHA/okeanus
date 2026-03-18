"""Embedding pipeline -- pgvector semantic search API router."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from okeanus.config import settings
from okeanus.db.postgres import get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml/embeddings", tags=["ml"])


@router.post("/search")
async def semantic_search(query: str, limit: int = 10, source_type: str | None = None) -> dict[str, Any]:
    """Semantic search over embedded ocean data using pgvector."""
    try:
        from okeanus.ml.vectors.search import VectorSearch
        searcher = VectorSearch()
        async with get_session() as session:
            results = await searcher.search(session, query, limit=limit, source_type=source_type)
        return {"status": "ok", "query": query, "count": len(results), "results": results}
    except ImportError:
        return {"status": "error", "message": "sentence-transformers not installed. Run: pip install okeanus[ml]"}
    except Exception as exc:
        logger.error("Semantic search failed: %s", exc)
        return {"status": "error", "message": str(exc)}


@router.post("/build")
async def build_index() -> dict[str, Any]:
    """Build the embedding index from all entities and events."""
    try:
        from okeanus.ml.vectors.indexer import EmbeddingIndexer
        indexer = EmbeddingIndexer()
        async with get_session() as session:
            counts = await indexer.build_full_index(session)
        return {"status": "ok", "message": "Embedding index built", "counts": counts}
    except ImportError:
        return {"status": "error", "message": "sentence-transformers not installed. Run: pip install okeanus[ml]"}
    except Exception as exc:
        logger.error("Build index failed: %s", exc)
        return {"status": "error", "message": str(exc)}


@router.get("/stats")
async def embedding_stats() -> dict[str, Any]:
    """Return embedding index statistics."""
    try:
        from okeanus.ml.vectors.indexer import EmbeddingIndexer
        indexer = EmbeddingIndexer()
        async with get_session() as session:
            stats = await indexer.embedding_stats(session)
        return {"status": "ok", **stats}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


@router.post("/similar/{source_id}")
async def find_similar(source_id: str, limit: int = 10) -> dict[str, Any]:
    """Find items similar to an existing embedded item."""
    try:
        from uuid import UUID
        from okeanus.ml.vectors.search import VectorSearch
        searcher = VectorSearch()
        async with get_session() as session:
            results = await searcher.find_similar(session, UUID(source_id), limit=limit)
        return {"status": "ok", "source_id": source_id, "count": len(results), "results": results}
    except Exception as exc:
        logger.error("Find similar failed: %s", exc)
        return {"status": "error", "message": str(exc)}
