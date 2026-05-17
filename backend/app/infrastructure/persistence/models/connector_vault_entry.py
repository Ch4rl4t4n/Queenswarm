"""Persisted connector credential envelope (Fernet at-rest encryption)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class ConnectorVaultEntry(Base, TimestampMixin, TenantScopedMixin):
    """Stores encrypted JSON blobs for MCP / third-party connector auth."""

    __tablename__ = "connector_vault_entries"

    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    credential_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    encrypted_payload: Mapped[str] = mapped_column(Text, nullable=False)
    dashboard_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id"),
        nullable=False,
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)

    def __repr__(self) -> str:  # noqa: D105
        return f"ConnectorVaultEntry(slug={self.slug!r}, kind={self.credential_kind!r})"
