"""pgvector semantic search over embeddings table."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.ml.vectors.embedder import OceanEmbedder

logger = logging.getLogger(__name__)


class VectorSearch:
    """Semantic search using pgvector cosine distance."""

    def __init__(self) -> None:
        self._embedder = OceanEmbedder()

    async def search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 10,
        source_type: str | None = None,
        min_similarity: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Find semantically similar items to the query text."""
        query_vec = self._embedder.embed_single(query)
        vec_str = "[" + ",".join(str(float(v)) for v in query_vec) + "]"

        type_filter = ""
        params: dict[str, Any] = {"vec": vec_str, "lim": limit, "min_sim": min_similarity}
        if source_type:
            type_filter = "AND source_type = :stype"
            params["stype"] = source_type

        sql = text(f"""
            SELECT id, source_id, source_type, source_table, text_content,
                   1 - (embedding <=> :vec::vector) AS similarity
            FROM embeddings
            WHERE 1 - (embedding <=> :vec::vector) >= :min_sim
            {type_filter}
            ORDER BY embedding <=> :vec::vector
            LIMIT :lim
        """)

        rows = (await session.execute(sql, params)).fetchall()
        return [
            {
                "id": str(row.id),
                "source_id": str(row.source_id),
                "source_type": row.source_type,
                "source_table": row.source_table,
                "text_content": row.text_content,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    async def find_similar(
        self,
        session: AsyncSession,
        source_id: UUID,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find items similar to an existing embedded item."""
        sql = text("""
            SELECT e2.id, e2.source_id, e2.source_type, e2.source_table,
                   e2.text_content,
                   1 - (e1.embedding <=> e2.embedding) AS similarity
            FROM embeddings e1
            JOIN embeddings e2 ON e1.id != e2.id
            WHERE e1.source_id = :sid
            ORDER BY e1.embedding <=> e2.embedding
            LIMIT :lim
        """)
        rows = (await session.execute(sql, {"sid": str(source_id), "lim": limit})).fetchall()
        return [
            {
                "id": str(row.id),
                "source_id": str(row.source_id),
                "source_type": row.source_type,
                "source_table": row.source_table,
                "text_content": row.text_content,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    async def cross_domain_similar(
        self,
        session: AsyncSession,
        query: str,
        exclude_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find similar items across different source types (cross-domain discovery)."""
        query_vec = self._embedder.embed_single(query)
        vec_str = "[" + ",".join(str(float(v)) for v in query_vec) + "]"

        exclude_filter = ""
        params: dict[str, Any] = {"vec": vec_str, "lim": limit}
        if exclude_type:
            exclude_filter = "AND source_type != :etype"
            params["etype"] = exclude_type

        sql = text(f"""
            SELECT id, source_id, source_type, source_table, text_content,
                   1 - (embedding <=> :vec::vector) AS similarity
            FROM embeddings
            WHERE 1 - (embedding <=> :vec::vector) >= 0.25
            {exclude_filter}
            ORDER BY embedding <=> :vec::vector
            LIMIT :lim
        """)
        rows = (await session.execute(sql, params)).fetchall()
        return [
            {
                "id": str(row.id),
                "source_id": str(row.source_id),
                "source_type": row.source_type,
                "source_table": row.source_table,
                "text_content": row.text_content,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]
