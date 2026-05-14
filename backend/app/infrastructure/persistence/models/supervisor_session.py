"""Dynamic supervisor sessions + sub-agent runtime telemetry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class SupervisorSession(Base, TimestampMixin):
    """Top-level orchestration envelope for dynamic sub-agent swarms."""

    __tablename__ = "supervisor_sessions"

    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    runtime_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="inprocess")
    created_by_subject: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    context_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    swarm_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sub_swarms.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    sub_agents: Mapped[list["SubAgentSession"]] = relationship(
        "SubAgentSession",
        back_populates="supervisor_session",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["SupervisorSessionEvent"]] = relationship(
        "SupervisorSessionEvent",
        back_populates="supervisor_session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return concise supervisor diagnostics."""

        return (
            f"SupervisorSession(id={self.id!s}, status={self.status!r}, "
            f"runtime_mode={self.runtime_mode!r})"
        )


class SubAgentSession(Base, TimestampMixin):
    """Runtime sub-agent row belonging to one supervisor orchestration."""

    __tablename__ = "sub_agent_sessions"

    supervisor_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supervisor_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    runtime_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="inprocess")
    toolset: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    short_memory: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    spawn_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    supervisor_session: Mapped["SupervisorSession"] = relationship(
        "SupervisorSession",
        back_populates="sub_agents",
    )
    events: Mapped[list["SupervisorSessionEvent"]] = relationship(
        "SupervisorSessionEvent",
        back_populates="sub_agent_session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return concise sub-agent diagnostics."""

        return f"SubAgentSession(id={self.id!s}, role={self.role!r}, status={self.status!r})"


class SupervisorSessionEvent(Base, TimestampMixin):
    """Structured timeline event for supervisor and sub-agent dashboards."""

    __tablename__ = "supervisor_session_events"

    supervisor_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("supervisor_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sub_agent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sub_agent_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True,
    )

    supervisor_session: Mapped["SupervisorSession"] = relationship(
        "SupervisorSession",
        back_populates="events",
    )
    sub_agent_session: Mapped["SubAgentSession | None"] = relationship(
        "SubAgentSession",
        back_populates="events",
    )

    def __repr__(self) -> str:
        """Return concise event diagnostics."""

        return f"SupervisorSessionEvent(id={self.id!s}, event_type={self.event_type!r})"

