"""Agent self-proposed improvement suggestions with supervisor governance."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class AgentSuggestion(Base, TimestampMixin, TenantScopedMixin):
    """Improvement proposal raised by agent initiative after reflection cycles."""

    __tablename__ = "agent_suggestions"

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
    proposal_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    proposed_by_role: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(260), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    proposal_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="low", index=True)
    impact_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    requires_manual_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    evaluation_reason: Mapped[str | None] = mapped_column(String(800), nullable=True)
    reviewed_by_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    implemented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """Return concise diagnostics for logs/debug."""

        return (
            f"AgentSuggestion(id={self.id!s}, type={self.proposal_type!r}, role={self.proposed_by_role!r}, "
            f"status={self.status!r}, risk={self.risk_level!r})"
        )


__all__ = ["AgentSuggestion"]
