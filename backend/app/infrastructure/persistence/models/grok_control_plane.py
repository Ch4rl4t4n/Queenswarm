"""Persistent Grok Control Plane run ledger and audit artifacts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class GrokRunORM(Base, TimestampMixin, TenantScopedMixin):
    """Top-level Grok run row (objective, mode, status, policy gates)."""

    __tablename__ = "grok_runs"

    dashboard_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    scope_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    run_mode: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    command_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    requires_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    def __repr__(self) -> str:
        """Return concise run diagnostics."""

        return f"GrokRunORM(id={self.id!s}, status={self.status!r}, mode={self.run_mode!r})"


class GrokRunStepORM(Base, TimestampMixin, TenantScopedMixin):
    """Ordered run step (plan/command/verify/deploy) and execution result."""

    __tablename__ = "grok_run_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grok_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    command: Mapped[str | None] = mapped_column(Text, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """Return concise step diagnostics."""

        return f"GrokRunStepORM(id={self.id!s}, run_id={self.run_id!s}, step_id={self.step_id!r})"


class GrokRunEventORM(Base, TimestampMixin, TenantScopedMixin):
    """Immutable timeline event for run auditing."""

    __tablename__ = "grok_run_events"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grok_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )

    def __repr__(self) -> str:
        """Return concise event diagnostics."""

        return f"GrokRunEventORM(id={self.id!s}, code={self.code!r}, level={self.level!r})"


class GrokRunApprovalORM(Base, TimestampMixin, TenantScopedMixin):
    """Explicit operator approval/rejection decision rows."""

    __tablename__ = "grok_run_approvals"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grok_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    decided_by: Mapped[str] = mapped_column(String(256), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )

    def __repr__(self) -> str:
        """Return concise approval diagnostics."""

        return f"GrokRunApprovalORM(id={self.id!s}, decision={self.decision!r})"


class GrokRunArtifactORM(Base, TimestampMixin, TenantScopedMixin):
    """Durable generated artifact row (logs, plan markdown, diff/test bundle)."""

    __tablename__ = "grok_run_artifacts"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("grok_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False, default="text/plain")
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    def __repr__(self) -> str:
        """Return concise artifact diagnostics."""

        return f"GrokRunArtifactORM(id={self.id!s}, kind={self.artifact_kind!r})"


class GrokRunTemplateORM(Base, TimestampMixin, TenantScopedMixin):
    """Reusable run intake template managed by operator."""

    __tablename__ = "grok_run_templates"

    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    scope_paths: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    run_mode: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    command_profile: Mapped[str] = mapped_column(String(64), nullable=False)
    context_sources: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(nullable=False, default=False, index=True)

    def __repr__(self) -> str:
        """Return concise template diagnostics."""

        return f"GrokRunTemplateORM(id={self.id!s}, name={self.name!r}, archived={self.is_archived})"


__all__ = [
    "GrokRunORM",
    "GrokRunStepORM",
    "GrokRunEventORM",
    "GrokRunApprovalORM",
    "GrokRunArtifactORM",
    "GrokRunTemplateORM",
]
