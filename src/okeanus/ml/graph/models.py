"""Knowledge graph ORM models and Pydantic schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import DateTime, Float, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Base


class EdgeType(str, enum.Enum):
    IS_A = "IS_A"
    RELATES_TO = "RELATES_TO"
    INFLUENCES = "INFLUENCES"
    CAUSES = "CAUSES"
    CONTRADICTS = "CONTRADICTS"
    PRECEDES = "PRECEDES"
    CO_OCCURS = "CO_OCCURS"
    SPATIALLY_NEAR = "SPATIALLY_NEAR"
    CORRELATES_WITH = "CORRELATES_WITH"
    IDENTITY = "IDENTITY"
    OPERATES_IN = "OPERATES_IN"
    REGULATED_BY = "REGULATED_BY"
    SOURCED_FROM = "SOURCED_FROM"


class NodeType(str, enum.Enum):
    ENTITY = "entity"
    OBSERVATION = "observation"
    EVENT = "event"
    TIMESERIES = "timeseries"
    FINDING = "finding"


class KnowledgeEdge(Base):
    """A typed, weighted edge in the knowledge graph."""

    __tablename__ = "knowledge_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Source node
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Target node
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_label: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Edge metadata
    edge_type: Mapped[str] = mapped_column(String(30), nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    evidence_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    evidence_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_ke_source", "source_id", "source_type"),
        Index("ix_ke_target", "target_id", "target_type"),
        Index("ix_ke_edge_type", "edge_type"),
        Index("ix_ke_domain", "domain"),
    )


class KnowledgeEdgeCreate(BaseModel):
    """Pydantic model for creating a knowledge edge."""

    source_id: uuid.UUID
    source_type: str
    source_label: str | None = None
    target_id: uuid.UUID
    target_type: str
    target_label: str | None = None
    edge_type: str
    strength: float = 1.0
    evidence_type: str | None = None
    evidence_detail: str | None = None
    domain: str | None = None
    payload: dict[str, Any] | None = None


class KnowledgeEdgeRead(BaseModel):
    """Pydantic model for reading a knowledge edge."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_id: uuid.UUID
    source_type: str
    source_label: str | None = None
    target_id: uuid.UUID
    target_type: str
    target_label: str | None = None
    edge_type: str
    strength: float
    evidence_type: str | None = None
    evidence_detail: str | None = None
    domain: str | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime
