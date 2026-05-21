"""Persistence model for Auto-Graphify folder ingest batches."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.infrastructure.persistence.models.base import TenantScopedMixin


class GraphifyStatusORM(StrEnum):
    """Lifecycle status for one Auto-Graphify batch."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GraphifyBatchORM(Base, TenantScopedMixin):
    """Folder upload queued for vault mirror + Neo4j graph + vector embed."""

    __tablename__ = "graphify_batches"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by_subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    status: Mapped[GraphifyStatusORM] = mapped_column(
        String(24),
        nullable=False,
        default=GraphifyStatusORM.QUEUED,
        index=True,
    )
    folder_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_ingested: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graph_nodes_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vectors_embedded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pollen_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    vault_rel_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
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

        return f"GraphifyBatchORM(id={self.id!s}, status={self.status!r})"


__all__ = ["GraphifyBatchORM", "GraphifyStatusORM"]
