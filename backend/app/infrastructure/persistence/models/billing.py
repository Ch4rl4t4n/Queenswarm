"""Tenant billing + subscription persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.infrastructure.persistence.models.base import TenantScopedMixin


class TenantSubscription(Base, TenantScopedMixin):
    """Current plan envelope for one tenant (billing-ready foundation)."""

    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    tier: Mapped[str] = mapped_column(String(32), nullable=False, default="free", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    billing_cycle_anchor: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    limits_override: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    feature_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    def __repr__(self) -> str:
        """Return concise billing diagnostics."""

        return f"TenantSubscription(id={self.id!s}, tier={self.tier!r}, status={self.status!r})"


__all__ = ["TenantSubscription"]
