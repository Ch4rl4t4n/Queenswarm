"""Tenant-scoped skill picker usage tallies for compact favorites."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin


class TenantSkillPickerUsageORM(Base, TimestampMixin, TenantScopedMixin):
    """How often an operator manually picks each skill in session/task pickers."""

    __tablename__ = "tenant_skill_picker_usage"
    __table_args__ = (
        UniqueConstraint("tenant_id", "skill_slug", name="uq_tenant_skill_picker_usage_tenant_slug"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return (
            f"TenantSkillPickerUsageORM(slug={self.skill_slug!r}, "
            f"usage_count={self.usage_count}, tenant_id={self.tenant_id})"
        )


__all__ = ["TenantSkillPickerUsageORM"]
