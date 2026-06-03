"""Skill Factory market opportunity rows — research → build queue."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class SkillOpportunityORM(Base, TimestampMixin, TenantScopedMixin):
    """One researched niche candidate for Skill Factory production."""

    __tablename__ = "skill_opportunities"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    niche: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    competition_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    buildability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    suggested_price_eur_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=1900)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source_refs: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    supervisor_session_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    tenant_skill_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenant_skills.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"SkillOpportunityORM(niche={self.niche!r}, status={self.status!r})"


__all__ = ["SkillOpportunityORM"]
