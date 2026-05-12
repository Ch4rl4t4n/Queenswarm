"""Dashboard operator accounts with password + TOTP (hive control plane login)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, DateTime, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class DashboardUser(Base, TimestampMixin):
    """Human operator row for Neon dashboard SSO (distinct from swarm ``Agent`` identities)."""

    __tablename__ = "dashboard_users"
    __table_args__ = (UniqueConstraint("email", name="uq_dashboard_users_email"),)

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(96), nullable=True)
    notification_prefs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_verified_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    totp_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        """Return a redacted overview for structured logs."""

        return f"DashboardUser(id={self.id!s}, email={self.email!r})"
