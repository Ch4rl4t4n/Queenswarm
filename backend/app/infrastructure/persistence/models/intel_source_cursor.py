"""Per-source scrape watermarks for social intel foragers."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class IntelSourceCursorORM(Base, TimestampMixin, TenantScopedMixin):
    """Tracks last ingested external id per monitored channel/account."""

    __tablename__ = "intel_source_cursors"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "forager_id",
            "platform",
            "source_key",
            name="uq_intel_source_cursors_forager_source",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forager_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("foragers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    source_key: Mapped[str] = mapped_column(String(255), nullable=False)
    last_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backfill_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        """Return concise cursor diagnostics."""

        return (
            f"IntelSourceCursorORM(forager_id={self.forager_id!s}, "
            f"platform={self.platform!r}, source_key={self.source_key!r})"
        )


__all__ = ["IntelSourceCursorORM"]
