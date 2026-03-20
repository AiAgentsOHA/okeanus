"""Temporal reasoning engine -- event sequence detection and causal chain discovery.

Finds temporally ordered event sequences from different sources within
spatial proximity, discovers recurring patterns, and matches against
known causal templates.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

import numpy as np
from scipy import stats
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from okeanus.ml.graph.models import EdgeType, KnowledgeEdge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known causal pattern templates
# ---------------------------------------------------------------------------

KNOWN_PATTERNS = [
    {"name": "storm_flood_claims", "sequence": ["storm", "flood_claim"], "max_lag_days": 30},
    {"name": "earthquake_tsunami", "sequence": ["earthquake", "tsunami"], "max_lag_days": 1},
    {"name": "heatwave_bleaching", "sequence": ["marine_heatwave", "coral_bleaching"], "max_lag_days": 90},
    {"name": "spill_contamination", "sequence": ["oil_spill", "contamination"], "max_lag_days": 60},
    {"name": "cyclone_damage", "sequence": ["cyclone", "infrastructure_damage"], "max_lag_days": 7},
    {"name": "drought_fish_decline", "sequence": ["drought", "fish_stock_decline"], "max_lag_days": 180},
]


class TemporalReasoningEngine:
    """Discover temporal patterns and causal chains in event data."""

    # ------------------------------------------------------------------
    # 1. Detect event sequences
    # ------------------------------------------------------------------

    async def detect_event_sequences(
        self,
        session: AsyncSession,
        time_window_days: int = 30,
        spatial_radius_km: float = 100.0,
        min_sequence_length: int = 2,
    ) -> list[dict[str, Any]]:
        """Find temporally ordered event sequences from different sources
        within spatial proximity.

        Returns sequences of events that occur close in space and time
        from different data sources, suggesting potential causal links.
        """
        sql = text("""
            WITH event_pairs AS (
                SELECT
                    e1.id AS id_a,
                    e2.id AS id_b,
                    e1.event_type AS type_a,
                    e2.event_type AS type_b,
                    e1.source_name AS source_a,
                    e2.source_name AS source_b,
                    e1.timestamp AS ts_a,
                    e2.timestamp AS ts_b,
                    e1.name AS name_a,
                    e2.name AS name_b,
                    EXTRACT(EPOCH FROM (e2.timestamp - e1.timestamp)) / 86400.0 AS lag_days,
                    CASE
                        WHEN e1.geometry IS NOT NULL AND e2.geometry IS NOT NULL
                        THEN ST_Distance(e1.geometry::geography, e2.geometry::geography) / 1000.0
                        ELSE NULL
                    END AS distance_km,
                    CASE
                        WHEN e1.geometry IS NOT NULL
                        THEN ST_X(e1.geometry::geometry)
                        ELSE NULL
                    END AS lon,
                    CASE
                        WHEN e1.geometry IS NOT NULL
                        THEN ST_Y(e1.geometry::geometry)
                        ELSE NULL
                    END AS lat
                FROM events e1
                JOIN events e2
                    ON e1.id != e2.id
                    AND e1.source_name != e2.source_name
                    AND e2.timestamp > e1.timestamp
                    AND e2.timestamp <= e1.timestamp + make_interval(days => :window_days)
                WHERE e1.geometry IS NOT NULL
                  AND e2.geometry IS NOT NULL
                  AND ST_DWithin(
                      e1.geometry::geography,
                      e2.geometry::geography,
                      :radius_m
                  )
                ORDER BY e1.timestamp, lag_days
                LIMIT 500
            )
            SELECT * FROM event_pairs
        """)

        rows = (await session.execute(sql, {
            "window_days": time_window_days,
            "radius_m": spatial_radius_km * 1000,
        })).fetchall()

        # Group into sequences by spatial proximity
        sequences: list[dict[str, Any]] = []
        seen_pairs: set[tuple] = set()

        for row in rows:
            pair_key = (str(row.id_a), str(row.id_b))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            lag = float(row.lag_days)
            dist = float(row.distance_km) if row.distance_km else None

            # Confidence based on temporal proximity and spatial closeness
            time_conf = max(0, 1.0 - lag / time_window_days)
            spatial_conf = max(0, 1.0 - (dist or 0) / spatial_radius_km) if dist else 0.5
            confidence = round((time_conf + spatial_conf) / 2, 3)

            sequences.append({
                "sequence": [row.type_a, row.type_b],
                "events": [
                    {"id": str(row.id_a), "type": row.type_a, "source": row.source_a,
                     "name": row.name_a, "timestamp": str(row.ts_a)},
                    {"id": str(row.id_b), "type": row.type_b, "source": row.source_b,
                     "name": row.name_b, "timestamp": str(row.ts_b)},
                ],
                "time_span_days": round(lag, 2),
                "distance_km": round(dist, 1) if dist else None,
                "spatial_center": [float(row.lon), float(row.lat)] if row.lon else None,
                "confidence": confidence,
            })

        # Sort by confidence descending
        sequences.sort(key=lambda x: x["confidence"], reverse=True)
        logger.info("Detected %d event sequences", len(sequences))
        return sequences

    # ------------------------------------------------------------------
    # 2. Discover causal chains (recurring patterns)
    # ------------------------------------------------------------------

    async def discover_causal_chains(
        self,
        session: AsyncSession,
        min_occurrences: int = 3,
        time_window_days: int = 60,
        spatial_radius_km: float = 200.0,
    ) -> list[dict[str, Any]]:
        """Find recurring event sequences that suggest causal relationships.

        Uses chi-squared test for statistical significance: tests whether
        event B follows event A more often than expected by chance.
        Returns PRECEDES/CAUSES edge candidates for the knowledge graph.
        """
        # Get all event type pairs with co-occurrence counts
        sql = text("""
            WITH pairs AS (
                SELECT
                    e1.event_type AS type_a,
                    e2.event_type AS type_b,
                    COUNT(*) AS co_count
                FROM events e1
                JOIN events e2
                    ON e1.id != e2.id
                    AND e1.source_name != e2.source_name
                    AND e2.timestamp > e1.timestamp
                    AND e2.timestamp <= e1.timestamp + make_interval(days => :window_days)
                    AND (
                        e1.geometry IS NULL
                        OR e2.geometry IS NULL
                        OR ST_DWithin(
                            e1.geometry::geography,
                            e2.geometry::geography,
                            :radius_m
                        )
                    )
                GROUP BY e1.event_type, e2.event_type
                HAVING COUNT(*) >= :min_occ
            ),
            type_counts AS (
                SELECT event_type, COUNT(*) AS total
                FROM events
                GROUP BY event_type
            )
            SELECT
                p.type_a,
                p.type_b,
                p.co_count,
                ta.total AS total_a,
                tb.total AS total_b,
                (SELECT COUNT(*) FROM events) AS total_events
            FROM pairs p
            JOIN type_counts ta ON ta.event_type = p.type_a
            JOIN type_counts tb ON tb.event_type = p.type_b
            ORDER BY p.co_count DESC
        """)

        rows = (await session.execute(sql, {
            "window_days": time_window_days,
            "radius_m": spatial_radius_km * 1000,
            "min_occ": min_occurrences,
        })).fetchall()

        chains: list[dict[str, Any]] = []
        for row in rows:
            total = row.total_events
            if total == 0:
                continue

            # Chi-squared test: is co-occurrence more than expected?
            observed = row.co_count
            p_a = row.total_a / total
            p_b = row.total_b / total
            expected = p_a * p_b * total

            if expected < 1:
                continue

            # Chi-squared statistic
            chi2 = ((observed - expected) ** 2) / expected
            p_value = float(1 - stats.chi2.cdf(chi2, df=1))

            edge_type = "CAUSES" if p_value < 0.01 and observed > 2 * expected else "PRECEDES"

            chains.append({
                "type_a": row.type_a,
                "type_b": row.type_b,
                "co_occurrences": row.co_count,
                "expected": round(expected, 2),
                "chi_squared": round(chi2, 4),
                "p_value": round(p_value, 6),
                "significant": p_value < 0.05,
                "edge_type": edge_type,
                "total_a": row.total_a,
                "total_b": row.total_b,
            })

        chains.sort(key=lambda x: x["p_value"])
        logger.info("Discovered %d causal chain candidates", len(chains))
        return chains

    # ------------------------------------------------------------------
    # 3. Match known patterns
    # ------------------------------------------------------------------

    async def match_known_patterns(
        self,
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Match observations against known causal pattern templates."""
        matches: list[dict[str, Any]] = []

        for pattern in KNOWN_PATTERNS:
            seq = pattern["sequence"]
            max_lag = pattern["max_lag_days"]

            if len(seq) < 2:
                continue

            type_a = seq[0]
            type_b = seq[1]

            sql = text("""
                SELECT
                    e1.id AS id_a,
                    e2.id AS id_b,
                    e1.event_type AS type_a,
                    e2.event_type AS type_b,
                    e1.name AS name_a,
                    e2.name AS name_b,
                    e1.timestamp AS ts_a,
                    e2.timestamp AS ts_b,
                    EXTRACT(EPOCH FROM (e2.timestamp - e1.timestamp)) / 86400.0 AS lag_days
                FROM events e1
                JOIN events e2
                    ON e1.id != e2.id
                    AND e2.timestamp > e1.timestamp
                    AND e2.timestamp <= e1.timestamp + make_interval(days => :max_lag)
                WHERE e1.event_type ILIKE :type_a
                  AND e2.event_type ILIKE :type_b
                ORDER BY e1.timestamp
                LIMIT 100
            """)

            rows = (await session.execute(sql, {
                "type_a": f"%{type_a}%",
                "type_b": f"%{type_b}%",
                "max_lag": max_lag,
            })).fetchall()

            if rows:
                matches.append({
                    "pattern_name": pattern["name"],
                    "sequence": seq,
                    "max_lag_days": max_lag,
                    "match_count": len(rows),
                    "instances": [
                        {
                            "event_a": {"id": str(r.id_a), "type": r.type_a,
                                        "name": r.name_a, "timestamp": str(r.ts_a)},
                            "event_b": {"id": str(r.id_b), "type": r.type_b,
                                        "name": r.name_b, "timestamp": str(r.ts_b)},
                            "lag_days": round(float(r.lag_days), 2),
                        }
                        for r in rows[:10]  # cap instances
                    ],
                })

        logger.info("Matched %d known patterns", len(matches))
        return matches

    # ------------------------------------------------------------------
    # 4. Create knowledge graph edges from discoveries
    # ------------------------------------------------------------------

    async def create_graph_edges(
        self,
        session: AsyncSession,
        chains: list[dict[str, Any]],
    ) -> int:
        """Persist discovered causal chains as knowledge graph edges.

        Only creates edges for statistically significant discoveries.
        """
        count = 0
        for chain in chains:
            if not chain.get("significant"):
                continue

            edge_type = chain.get("edge_type", "PRECEDES")

            edge = KnowledgeEdge(
                id=uuid.uuid4(),
                source_id=uuid.uuid4(),  # synthetic node for event type
                source_type="event_type",
                source_label=chain["type_a"],
                target_id=uuid.uuid4(),
                target_type="event_type",
                target_label=chain["type_b"],
                edge_type=edge_type,
                strength=round(1.0 - chain["p_value"], 4),
                evidence_type="statistical",
                evidence_detail=(
                    f"Chi-squared={chain['chi_squared']:.3f}, p={chain['p_value']:.4f}, "
                    f"observed={chain['co_occurrences']}, expected={chain['expected']:.1f}"
                ),
                domain="temporal_reasoning",
                payload={
                    "co_occurrences": chain["co_occurrences"],
                    "chi_squared": chain["chi_squared"],
                    "p_value": chain["p_value"],
                },
            )
            session.add(edge)
            count += 1

        if count:
            await session.flush()
            logger.info("Created %d knowledge graph edges from temporal reasoning", count)
        return count
