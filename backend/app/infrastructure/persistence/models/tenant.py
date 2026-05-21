"""Tenant entities for multi-user/team data isolation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class Tenant(Base, TimestampMixin):
    """Organization/team boundary used for row-level data isolation."""

    __tablename__ = "tenants"
    __table_args__ = (UniqueConstraint("slug", name="uq_tenants_slug"),)

    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    platform_mode: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default="internal",
        index=True,
    )
    operator_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    def __repr__(self) -> str:
        """Return tenant diagnostics."""

        return f"Tenant(id={self.id!s}, slug={self.slug!r})"


class DashboardUserTenantMembership(Base, TimestampMixin):
    """Membership mapping between dashboard operators and tenants."""

    __tablename__ = "dashboard_user_tenants"
    __table_args__ = (
        UniqueConstraint("dashboard_user_id", "tenant_id", name="uq_dashboard_user_tenant_membership"),
    )

    dashboard_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        """Return membership diagnostics."""

        return (
            f"DashboardUserTenantMembership(user_id={self.dashboard_user_id!s}, "
            f"tenant_id={self.tenant_id!s}, role={self.role!r})"
        )


class TenantInvite(Base, TimestampMixin, TenantScopedMixin):
    """Pending tenant invite sent to an email address."""

    __tablename__ = "tenant_invites"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invite_token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")

    def __repr__(self) -> str:
        """Return invite diagnostics."""

        return f"TenantInvite(email={self.email!r}, role={self.role!r}, status={self.status!r})"


class TenantAuditLog(Base, TimestampMixin, TenantScopedMixin):
    """Audit log entries for tenant role/invite/member management actions."""

    __tablename__ = "tenant_audit_logs"

    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    def __repr__(self) -> str:
        """Return audit diagnostics."""

        return f"TenantAuditLog(action={self.action!r}, target={self.target_type!r}:{self.target_ref!r})"


__all__ = [
    "Tenant",
    "DashboardUserTenantMembership",
    "TenantInvite",
    "TenantAuditLog",
]
