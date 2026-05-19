"""Tenant-scoped dynamic Agent Template persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class AgentTemplateORM(Base, TimestampMixin, TenantScopedMixin):
    """Customizable tenant template used by `/agents/new` dynamic menu."""

    __tablename__ = "agent_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    icon: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    tools: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))

    def __repr__(self) -> str:
        """Return concise template diagnostics."""

        return (
            f"AgentTemplateORM(id={self.id!s}, tenant_id={self.tenant_id!s}, "
            f"name={self.name!r}, category={self.category!r})"
        )


__all__ = ["AgentTemplateORM"]
