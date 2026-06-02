"""Wiki Layer persistence — compiled wiki pages and gardener run audit."""

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


class WikiGardenerStatusORM(StrEnum):
    """Lifecycle for one Wiki Gardener sweep."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WikiLayerPageORM(Base, TenantScopedMixin):
    """Tenant-scoped compiled wiki page (hot tier — injected every prompt)."""

    __tablename__ = "wiki_layer_pages"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(96), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    content_md: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    char_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        """Return debug representation."""

        return f"WikiLayerPageORM(slug={self.slug!r}, version={self.version})"


class WikiGardenerRunORM(Base, TenantScopedMixin):
    """Audit row for one Wiki Gardener raw→wiki sweep."""

    __tablename__ = "wiki_gardener_runs"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=WikiGardenerStatusORM.RUNNING)
    summary_md: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    stats: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    pages_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pollen_awarded: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """Return debug representation."""

        return f"WikiGardenerRunORM(status={self.status!r}, pages_updated={self.pages_updated})"
