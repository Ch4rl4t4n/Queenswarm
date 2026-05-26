"""Tenant-scoped social platform accounts — unlimited OAuth connections per channel."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.infrastructure.persistence.models.base import TenantScopedMixin, TimestampMixin, UUIDMixin


class SocialConnectedAccount(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    """One connected social identity (X @user, IG business, FB Page, …) for a tenant."""

    __tablename__ = "social_connected_accounts"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "channel",
            "account_key",
            name="uq_social_connected_accounts_tenant_channel_key",
        ),
    )

    dashboard_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    account_key: Mapped[str] = mapped_column(String(256), nullable=False)
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    oauth_provider_key: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    external_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    profile_meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    secrets_cipher: Mapped[str] = mapped_column(Text, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")

    def __repr__(self) -> str:
        """Return a redacted representation."""

        return (
            f"SocialConnectedAccount(id={self.id!s}, channel={self.channel!r}, "
            f"label={self.label!r}, status={self.status!r})"
        )


__all__ = ["SocialConnectedAccount"]
