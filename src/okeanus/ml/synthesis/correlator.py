"""Cross-domain temporal/spatial/semantic correlation engine."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CorrelationEngine:
    """Discover correlations across domains using DuckDB analytics + pgvector."""

    async def temporal_correlation(
        self,
        session: AsyncSession,
        domain_a: str,
        domain_b: str,
        lag_days: int = 90,
        min_correlation: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Find temporal correlations between time series from different domains.

        Uses the existing DuckDB ts_correlation capability.
        """
        try:
            from okeanus.db.duckdb import DuckDBAnalytics
            analytics = DuckDBAnalytics()
            results = await analytics.ts_correlation(
                source_a=domain_a,
                source_b=domain_b,
                lag_periods=lag_days,
            )
            return [r for r in results if abs(r.get("correlation", 0)) >= min_correlation]
        except Exception as exc:
            logger.warning("Temporal correlation failed: %s", exc)
            return []

    async def spatial_co_occurrence(
        self,
        session: AsyncSession,
        radius_km: float = 50.0,
        min_events: int = 3,
    ) -> list[dict[str, Any]]:
        """Find spatially co-occurring events from different sources."""
        sql = text("""
            WITH event_pairs AS (
                SELECT
                    e1.source_name AS source_a,
                    e2.source_name AS source_b,
                    e1.event_type AS type_a,
                    e2.event_type AS type_b,
                    COUNT(*) AS co_occurrences,
                    AVG(ST_Distance(e1.geometry::geography, e2.geometry::geography)) / 1000 AS avg_dist_km
                FROM events e1
                JOIN events e2 ON e1.id < e2.id
                    AND e1.source_name != e2.source_name
                    AND ST_DWithin(e1.geometry::geography, e2.geometry::geography, :radius_m)
                    AND ABS(EXTRACT(EPOCH FROM (e1.created_at - e2.created_at))) < 86400 * 30
                WHERE e1.geometry IS NOT NULL AND e2.geometry IS NOT NULL
                GROUP BY e1.source_name, e2.source_name, e1.event_type, e2.event_type
                HAVING COUNT(*) >= :min_events
            )
            SELECT * FROM event_pairs
            ORDER BY co_occurrences DESC
            LIMIT 50
        """)
        rows = (await session.execute(sql, {
            "radius_m": radius_km * 1000,
            "min_events": min_events,
        })).fetchall()

        return [
            {
                "source_a": row.source_a,
                "source_b": row.source_b,
                "type_a": row.type_a,
                "type_b": row.type_b,
                "co_occurrences": row.co_occurrences,
                "avg_distance_km": round(float(row.avg_dist_km), 1) if row.avg_dist_km else None,
            }
            for row in rows
        ]

    async def semantic_similarity_clusters(
        self,
        session: AsyncSession,
        min_similarity: float = 0.7,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Find semantically similar items across different source types."""
        sql = text("""
            SELECT
                e1.source_id AS id_a, e1.source_type AS type_a, e1.text_content AS text_a,
                e2.source_id AS id_b, e2.source_type AS type_b, e2.text_content AS text_b,
                1 - (e1.embedding <=> e2.embedding) AS similarity
            FROM embeddings e1
            JOIN embeddings e2 ON e1.id < e2.id
                AND e1.source_type != e2.source_type
            WHERE 1 - (e1.embedding <=> e2.embedding) >= :min_sim
            ORDER BY e1.embedding <=> e2.embedding
            LIMIT :lim
        """)
        rows = (await session.execute(sql, {"min_sim": min_similarity, "lim": limit})).fetchall()

        return [
            {
                "item_a": {"id": str(row.id_a), "type": row.type_a, "text": row.text_a[:200]},
                "item_b": {"id": str(row.id_b), "type": row.type_b, "text": row.text_b[:200]},
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    async def full_scan(
        self,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Run all correlation methods and return combined results."""
        results = []

        # Semantic clusters
        clusters = await self.semantic_similarity_clusters(session)
        for cluster in clusters:
            results.append({
                "correlation_type": "semantic",
                "confidence": cluster["similarity"],
                "description": f"Semantic similarity between {cluster['item_a']['type']} and {cluster['item_b']['type']}",
                "evidence": cluster,
            })

        # Spatial co-occurrence
        spatial = await self.spatial_co_occurrence(session)
        for sp in spatial:
            confidence = min(1.0, sp["co_occurrences"] / 10.0)
            results.append({
                "correlation_type": "spatial",
                "confidence": confidence,
                "description": f"Spatial co-occurrence: {sp['type_a']} ({sp['source_a']}) with {sp['type_b']} ({sp['source_b']})",
                "evidence": sp,
            })

        return sorted(results, key=lambda x: x["confidence"], reverse=True)
