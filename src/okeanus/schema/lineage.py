"""Lineage / provenance ORM models for data tracing."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from okeanus.schema.base import Base


class LineageNode(Base):
    """A node in the data lineage DAG."""

    __tablename__ = "lineage_nodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    node_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        doc="SOURCE, ADAPTER, TRANSFORM, ENTITY, EDGE, INSIGHT",
    )
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    table_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, doc="Which table this record lives in"
    )
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, doc="FK to the actual record"
    )
    source_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    transform_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, doc="Mapper or algorithm name"
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_lineage_nodes_type", "node_type"),
        Index("ix_lineage_nodes_record", "table_name", "record_id"),
        Index("ix_lineage_nodes_source", "source_name"),
    )


class LineageEdge(Base):
    """A directed edge in the lineage DAG."""

    __tablename__ = "lineage_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lineage_nodes.id"), nullable=False
    )
    child_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lineage_nodes.id"), nullable=False
    )
    edge_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        doc="PRODUCED_BY, DERIVED_FROM, CONTRIBUTED_TO",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_lineage_edges_parent", "parent_id"),
        Index("ix_lineage_edges_child", "child_id"),
        Index("ix_lineage_edges_type", "edge_type"),
    )
