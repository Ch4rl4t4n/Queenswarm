"""Persistence models for nightly dreaming consolidation cycles."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DreamCycleStatusORM(StrEnum):
    """DB lifecycle status for one dream cycle."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DreamCycleORM(Base):
    """Dream cycle summary row with counters, digest, and failure diagnostics."""

    __tablename__ = "dream_cycles"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[DreamCycleStatusORM] = mapped_column(
        SQLEnum(
            DreamCycleStatusORM,
            values_callable=lambda items: [item.value for item in items],
            native_enum=False,
            length=24,
        ),
        nullable=False,
        default=DreamCycleStatusORM.RUNNING,
        index=True,
    )
    items_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_deduplicated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_consolidated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    digest_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    traceback_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return concise developer representation."""

        return f"DreamCycleORM(id={self.id!s}, status={self.status.value!r})"


class DreamInsightORM(Base):
    """Consolidated insight produced by a dream cycle."""

    __tablename__ = "dream_insights"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dream_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_kind: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    neo4j_node_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    chroma_doc_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        """Return concise developer representation."""

        return f"DreamInsightORM(id={self.id!s}, cycle_id={self.cycle_id!s}, source_kind={self.source_kind!r})"


Index("ix_dream_cycles_started_at_status", DreamCycleORM.started_at, DreamCycleORM.status)
Index("ix_dream_insights_source_kind_created_at", DreamInsightORM.source_kind, DreamInsightORM.created_at)


__all__ = ["DreamCycleORM", "DreamCycleStatusORM", "DreamInsightORM"]
