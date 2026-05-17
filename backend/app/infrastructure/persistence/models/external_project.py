"""External integration registry — scoped projects, API keys, and run audit rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.infrastructure.persistence.models.base import TenantScopedMixin


class ExternalProject(Base, TenantScopedMixin):
    """Registered third-party application bridge (trading, ordering, custom)."""

    __tablename__ = "external_projects"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    project_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    owner_dashboard_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dashboard_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    webhook_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    webhook_secret_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("true"))

    api_keys: Mapped[list["ExternalProjectApiKey"]] = relationship(
        "ExternalProjectApiKey",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list["ExternalProjectRunAudit"]] = relationship(
        "ExternalProjectRunAudit",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Developer-safe summary."""

        return f"ExternalProject(id={self.id!s}, slug={self.slug!r}, kind={self.project_kind!r})"


class ExternalProjectApiKey(Base, TenantScopedMixin):
    """Per-project credential with permission scopes."""

    __tablename__ = "external_project_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str | None] = mapped_column(String(160), nullable=True)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    permissions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[\"run\"]'::jsonb"),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["ExternalProject"] = relationship("ExternalProject", back_populates="api_keys")

    def __repr__(self) -> str:
        """Developer-safe summary."""

        return (
            f"ExternalProjectApiKey(id={self.id!s}, project_id={self.project_id!s}, "
            f"revoked={self.revoked_at is not None})"
        )


class ExternalProjectRunAudit(Base, TenantScopedMixin):
    """Immutable audit + metrics slice for dashboards and Hive Mind mirrors."""

    __tablename__ = "external_project_run_audit"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("external_project_api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_slug: Mapped[str] = mapped_column(String(160), nullable=False)
    ok: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer(), nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, server_default=text("0"))
    human_approval_required: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        server_default=text("false"),
    )
    human_approved: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    payload_excerpt: Mapped[str] = mapped_column(Text(), nullable=False, server_default=text("''"))
    result_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    project: Mapped["ExternalProject"] = relationship("ExternalProject", back_populates="runs")

    def __repr__(self) -> str:
        """Developer-safe summary."""

        return (
            f"ExternalProjectRunAudit(id={self.id!s}, project={self.project_id!s}, "
            f"action={self.action_slug!r}, ok={self.ok})"
        )


__all__ = ["ExternalProject", "ExternalProjectApiKey", "ExternalProjectRunAudit"]
