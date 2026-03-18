"""Insight and reasoning trace ORM models + lifecycle management.

Includes feedback loop: user validation, calibration tracking, and
threshold tuning based on accumulated feedback.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import select

from okeanus.schema.base import Base


class InsightType(str, enum.Enum):
    CORRELATION = "correlation"
    ANOMALY_CLUSTER = "anomaly_cluster"
    BRIDGE_CONCEPT = "bridge_concept"
    CAUSAL_HYPOTHESIS = "causal_hypothesis"
    EMERGENT_PATTERN = "emergent_pattern"


class InsightStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    involved_domains: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    spatial_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    temporal_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    temporal_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    generator: Mapped[str | None] = mapped_column(String(100), nullable=True)
    critic_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    critic_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_ins_type", "insight_type"),
        Index("ix_ins_status", "status"),
        Index("ix_ins_confidence", "confidence"),
    )


class ReasoningTrace(Base):
    __tablename__ = "reasoning_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=True)
    phase: Mapped[str] = mapped_column(String(20), nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_rt_insight", "insight_id"),)


# -- Feedback loop models --

class InsightFeedback(Base):
    """User feedback on an insight — the core of the feedback loop.

    Tracks whether insights were correct, incorrect, or partially correct,
    enabling calibration analysis and threshold tuning.
    """
    __tablename__ = "insight_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)  # correct, incorrect, partial
    user_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0-1.0
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome_observed: Mapped[str | None] = mapped_column(Text, nullable=True)  # what actually happened
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_fb_insight", "insight_id"),
        Index("ix_fb_type", "feedback_type"),
        Index("ix_fb_created", "created_at"),
    )


class InsightManager:
    """Lifecycle management for insights with feedback loop and calibration."""

    async def create_insight(self, session: AsyncSession, **kwargs) -> Insight:
        insight = Insight(**kwargs)
        session.add(insight)
        await session.flush()
        return insight

    async def get_insights(
        self, session: AsyncSession,
        status: str | None = None,
        insight_type: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 50,
    ) -> list[Insight]:
        stmt = select(Insight).order_by(Insight.confidence.desc()).limit(limit)
        if status:
            stmt = stmt.where(Insight.status == status)
        if insight_type:
            stmt = stmt.where(Insight.insight_type == insight_type)
        if min_confidence > 0:
            stmt = stmt.where(Insight.confidence >= min_confidence)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def promote_insight(self, session: AsyncSession, insight_id: uuid.UUID, critic_score: float, critic_notes: str) -> None:
        insight = await session.get(Insight, insight_id)
        if insight:
            insight.critic_score = critic_score
            insight.critic_notes = critic_notes
            insight.status = "validated" if critic_score >= 0.6 else "rejected"

    async def add_trace(self, session: AsyncSession, insight_id: uuid.UUID | None, phase: str, input_text: str, output_text: str) -> ReasoningTrace:
        trace = ReasoningTrace(insight_id=insight_id, phase=phase, input_text=input_text, output_text=output_text)
        session.add(trace)
        await session.flush()
        return trace

    # -- Feedback loop methods --

    async def submit_feedback(
        self,
        session: AsyncSession,
        insight_id: uuid.UUID,
        feedback_type: str,
        user_score: float | None = None,
        notes: str | None = None,
        outcome_observed: str | None = None,
    ) -> InsightFeedback:
        """Record user feedback on an insight.

        feedback_type: 'correct', 'incorrect', or 'partial'
        user_score: optional 0.0-1.0 rating
        outcome_observed: what actually happened (for calibration)
        """
        fb = InsightFeedback(
            insight_id=insight_id,
            feedback_type=feedback_type,
            user_score=user_score,
            notes=notes,
            outcome_observed=outcome_observed,
        )
        session.add(fb)
        await session.flush()

        # Update insight status based on feedback
        insight = await session.get(Insight, insight_id)
        if insight:
            if feedback_type == "correct":
                insight.status = "validated"
            elif feedback_type == "incorrect":
                insight.status = "rejected"
            # 'partial' leaves status as-is

        return fb

    async def get_feedback(
        self,
        session: AsyncSession,
        insight_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[InsightFeedback]:
        """Get feedback records, optionally filtered by insight."""
        from sqlalchemy import select as sel
        stmt = sel(InsightFeedback).order_by(InsightFeedback.created_at.desc()).limit(limit)
        if insight_id:
            stmt = stmt.where(InsightFeedback.insight_id == insight_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def calibration_report(
        self,
        session: AsyncSession,
        bucket_count: int = 5,
    ) -> dict[str, Any]:
        """Compute calibration metrics: how well does predicted confidence match actual outcomes?

        Buckets insights by confidence level and computes the fraction
        that were confirmed correct by user feedback.
        Returns bucket-level stats + overall Brier score.
        """
        from sqlalchemy import text as sql_text

        # Get insights that have feedback
        sql = sql_text("""
            SELECT i.id, i.confidence, i.classification, i.insight_type,
                   fb.feedback_type, fb.user_score
            FROM insights i
            JOIN insight_feedback fb ON fb.insight_id = i.id
            ORDER BY i.confidence
        """)
        rows = (await session.execute(sql)).fetchall()

        if not rows:
            return {"buckets": [], "total_feedback": 0, "brier_score": None}

        # Build calibration buckets
        bucket_size = 1.0 / bucket_count
        buckets: list[dict[str, Any]] = []

        for b in range(bucket_count):
            low = b * bucket_size
            high = (b + 1) * bucket_size
            bucket_rows = [r for r in rows if low <= r.confidence < high or (b == bucket_count - 1 and r.confidence == 1.0)]

            if not bucket_rows:
                buckets.append({
                    "range": f"{low:.1f}-{high:.1f}",
                    "count": 0,
                    "predicted_avg": (low + high) / 2,
                    "actual_correct_rate": None,
                    "gap": None,
                })
                continue

            predicted_avg = sum(r.confidence for r in bucket_rows) / len(bucket_rows)
            correct_count = sum(1 for r in bucket_rows if r.feedback_type == "correct")
            actual_rate = correct_count / len(bucket_rows)

            buckets.append({
                "range": f"{low:.1f}-{high:.1f}",
                "count": len(bucket_rows),
                "predicted_avg": round(predicted_avg, 3),
                "actual_correct_rate": round(actual_rate, 3),
                "gap": round(predicted_avg - actual_rate, 3),
            })

        # Brier score: mean squared error between confidence and binary outcome
        brier_sum = 0.0
        for r in rows:
            outcome = 1.0 if r.feedback_type == "correct" else 0.0
            brier_sum += (r.confidence - outcome) ** 2
        brier_score = round(brier_sum / len(rows), 4)

        # Breakdown by classification
        class_stats: dict[str, dict[str, Any]] = {}
        for r in rows:
            cls = r.classification or "unknown"
            if cls not in class_stats:
                class_stats[cls] = {"total": 0, "correct": 0, "incorrect": 0, "partial": 0}
            class_stats[cls]["total"] += 1
            class_stats[cls][r.feedback_type] = class_stats[cls].get(r.feedback_type, 0) + 1

        for cls, stats in class_stats.items():
            if stats["total"] > 0:
                stats["accuracy"] = round(stats["correct"] / stats["total"], 3)

        return {
            "buckets": buckets,
            "total_feedback": len(rows),
            "brier_score": brier_score,
            "by_classification": class_stats,
            "interpretation": (
                "Brier score 0.0 = perfect calibration, 0.25 = random. "
                "Positive gap = overconfident, negative = underconfident."
            ),
        }
