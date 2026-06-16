"""Tenant-scoped local LLM adapter registry (GGUF / LoRA → Ollama tag)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class TenantLocalAdapterORM(Base, TimestampMixin, TenantScopedMixin):
    """Registered Ollama adapter for local_sovereign routing (Track M LOC8)."""

    __tablename__ = "tenant_local_adapters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ollama_tag", name="uq_tenant_local_adapters_tenant_tag"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ollama_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    litellm_slug: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="gguf")
    base_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    def __repr__(self) -> str:
        return (
            f"TenantLocalAdapterORM(tag={self.ollama_tag!r}, "
            f"slug={self.litellm_slug!r}, active={self.is_active})"
        )


__all__ = ["TenantLocalAdapterORM"]
