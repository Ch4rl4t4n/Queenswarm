"""PostgreSQL-backed dynamic connector descriptors (Phase 1.2 Dynamic Connector Hub)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class DynamicConnector(Base, TimestampMixin, TenantScopedMixin):
    """Runtime-configurable HTTP-style MCP manifests with vault-sealed operator secrets."""

    __tablename__ = "dynamic_connectors"

    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    #: Fernet ciphertext for :func:`app.connectors.secure_vault.seal_dynamic_connector_blob`
    secrets_cipher: Mapped[str | None] = mapped_column(Text, nullable=True)

    mcp_manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    allowed_manager_slugs: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    builtin_kind: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dashboard_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dashboard_users.id"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        """Return non-secret identity."""

        return f"DynamicConnector(slug={self.slug!r}, active={self.is_active!r}, builtin={self.is_builtin!r})"
