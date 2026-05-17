"""Browser harness persistence models for agent-driven web automation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class BrowserAutomationSession(Base, TimestampMixin, TenantScopedMixin):
    """One browser harness session controlled by a supervisor/sub-agent."""

    __tablename__ = "browser_automation_sessions"

    supervisor_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("supervisor_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sub_agent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sub_agent_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="headless", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="running", index=True)
    start_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    current_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    allowed_domains: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    blocked_reason: Mapped[str | None] = mapped_column(String(800), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_actions: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    actions_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_approval_action: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    last_snapshot_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_screenshot_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_headless: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """Return concise debug representation."""

        return (
            f"BrowserAutomationSession(id={self.id!s}, mode={self.mode!r}, status={self.status!r}, "
            f"actions={self.actions_used}/{self.max_actions})"
        )


class BrowserAutomationAction(Base, TimestampMixin, TenantScopedMixin):
    """Action log rows emitted by browser harness runs."""

    __tablename__ = "browser_automation_actions"

    browser_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("browser_automation_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="ok", index=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    result_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )

    def __repr__(self) -> str:
        """Return concise debug representation."""

        return f"BrowserAutomationAction(id={self.id!s}, type={self.action_type!r}, status={self.status!r})"


__all__ = ["BrowserAutomationAction", "BrowserAutomationSession"]
