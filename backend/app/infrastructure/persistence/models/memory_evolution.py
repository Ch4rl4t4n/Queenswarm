"""Memory evolution proposals for long-term swarm learning governance."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class MemoryEvolutionProposal(Base, TimestampMixin, TenantScopedMixin):
    """Proposed long-term memory updates that may require manual approval."""

    __tablename__ = "memory_evolution_proposals"

    proposal_kind: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", index=True)
    importance_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    requires_manual_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    proposed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        """Return concise diagnostics."""

        return (
            f"MemoryEvolutionProposal(id={self.id!s}, kind={self.proposal_kind!r}, "
            f"status={self.status!r}, importance={self.importance_score})"
        )


__all__ = ["MemoryEvolutionProposal"]
