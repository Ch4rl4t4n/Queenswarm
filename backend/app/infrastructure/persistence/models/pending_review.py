"""Operator pending-review gate for sub-threshold swarm outcomes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SQEnum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin
from app.infrastructure.persistence.models.enums import PendingReviewStatus


class PendingReviewItem(Base, TimestampMixin):
    """Human approval queue before low-confidence payloads reach operators."""

    __tablename__ = "pending_review_items"

    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    swarm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sub_swarms.id"), nullable=False)
    workflow_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workflows.id"), nullable=False)
    simulation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("simulations.id"), nullable=True)
    status: Mapped[PendingReviewStatus] = mapped_column(
        SQEnum(
            PendingReviewStatus,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=16,
        ),
        nullable=False,
        default=PendingReviewStatus.PENDING,
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_fraction: Mapped[float | None] = mapped_column(Float, nullable=True)
    verification_passed: Mapped[bool] = mapped_column(nullable=False, default=False)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return a concise debug representation."""

        return (
            f"PendingReviewItem(id={self.id!s}, status={self.status.value!r}, "
            f"reason={self.reason!r}, confidence_fraction={self.confidence_fraction})"
        )


__all__ = ["PendingReviewItem"]
