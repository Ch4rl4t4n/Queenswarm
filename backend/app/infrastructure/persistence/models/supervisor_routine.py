"""Scheduled supervisor routine definitions (lightweight control-plane automation)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class SupervisorRoutine(Base, TimestampMixin):
    """Recurring routine that can spawn supervisor sessions on a schedule."""

    __tablename__ = "supervisor_routines"

    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    goal_template: Mapped[str] = mapped_column(Text, nullable=False)
    schedule_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="interval")
    interval_seconds: Mapped[int | None] = mapped_column(nullable=True)
    cron_expr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="durable")
    roles: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    retrieval_contract: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skills: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    context_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="idle")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by_subject: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return concise routine diagnostics."""

        return f"SupervisorRoutine(id={self.id!s}, name={self.name!r}, status={self.status!r})"


__all__ = ["SupervisorRoutine"]
