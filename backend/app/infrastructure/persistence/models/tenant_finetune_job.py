"""Tenant-scoped GPU fine-tune job queue (Track M LOC9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.base import TenantScopedMixin

FinetuneJobStatus = str


class TenantFinetuneJobORM(Base, TimestampMixin, TenantScopedMixin):
    """Operator-approved QLoRA fine-tune job executed on GPU Celery worker."""

    __tablename__ = "tenant_finetune_jobs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_approval")
    adapter_name: Mapped[str] = mapped_column(String(64), nullable=False)
    base_model: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_source: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    epochs: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    approved_by_subject: Mapped[str | None] = mapped_column(String(256), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_plan_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    def __repr__(self) -> str:
        return (
            f"TenantFinetuneJobORM(adapter={self.adapter_name!r}, "
            f"status={self.status!r}, rows={self.dataset_row_count})"
        )


__all__ = ["TenantFinetuneJobORM"]
