"""Persistence model for Dump & Sleep overnight ingest batches."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.infrastructure.persistence.models.base import TenantScopedMixin


class DumpSleepStatusORM(StrEnum):
    """Lifecycle status for one overnight dump batch."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DumpSleepBatchORM(Base, TenantScopedMixin):
    """Overnight folder/voice dump queued for hive ingest + dreaming."""

    __tablename__ = "dump_sleep_batches"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by_subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[DumpSleepStatusORM] = mapped_column(
        String(24),
        nullable=False,
        default=DumpSleepStatusORM.QUEUED,
        index=True,
    )
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    voice_note_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    items_ingested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stalled_signals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pollen_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    briefing_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dream_cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dream_cycles.id", ondelete="SET NULL"),
        nullable=True,
    )
    storage_meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """Return concise developer representation."""

        return f"DumpSleepBatchORM(id={self.id!s}, status={self.status!r})"


__all__ = ["DumpSleepBatchORM", "DumpSleepStatusORM"]
