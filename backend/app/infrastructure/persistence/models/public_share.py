"""Public read-only share links for tenant resources."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class PublicShareLink(Base, TimestampMixin, TenantScopedMixin):
    """Share token linked to one resource and exposed via public read-only endpoint."""

    __tablename__ = "public_share_links"

    resource_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    share_token: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        """Return concise diagnostics for share rows."""

        return (
            f"PublicShareLink(id={self.id!s}, resource_type={self.resource_type!r}, "
            f"resource_id={self.resource_id!s}, active={self.is_active})"
        )


__all__ = ["PublicShareLink"]
