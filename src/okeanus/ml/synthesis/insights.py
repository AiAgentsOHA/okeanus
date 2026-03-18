"""Insight and reasoning trace ORM models + lifecycle management."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
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


class InsightManager:
    """Lifecycle management for insights."""

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
