"""Tenant-scoped custom skills produced by Skill Factory."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class TenantSkillORM(Base, TimestampMixin, TenantScopedMixin):
    """One tenant-owned markdown skill loadable by SkillLibrary at runtime."""

    __tablename__ = "tenant_skills"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    markdown_body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    roles: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    keywords: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="factory")
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    github_exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"TenantSkillORM(slug={self.slug!r}, tenant_id={self.tenant_id})"

    def to_skill_meta(self) -> dict[str, Any]:
        """Frontmatter-compatible metadata for SkillLibrary overlay."""

        return {
            "version": self.version,
            "priority": self.priority,
            "roles": list(self.roles or []),
            "keywords": list(self.keywords or []),
        }


__all__ = ["TenantSkillORM"]
