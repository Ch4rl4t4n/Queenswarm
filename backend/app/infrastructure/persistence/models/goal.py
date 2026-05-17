"""Persistence models for Queen goal orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class GoalStatusORM(StrEnum):
    """Persisted goal status enum."""

    PENDING = "pending"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    AUDITING = "auditing"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED_BY_BUDGET = "halted_by_budget"
    HALTED_BY_HUMAN = "halted_by_human"


class GoalORM(Base, TimestampMixin):
    """Top-level tenant goal row."""

    __tablename__ = "goals"
    __tenant_scoped__ = True

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("dashboard_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    acceptance_criteria_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    max_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    budget_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[GoalStatusORM] = mapped_column(
        SQLEnum(
            GoalStatusORM,
            values_callable=lambda items: [item.value for item in items],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=GoalStatusORM.PENDING,
        index=True,
    )
    current_iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Intentional soft link to task ledger row (no DB FK constraint by design).
    root_task_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    halt_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    spent_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    audits: Mapped[list["GoalAuditResultORM"]] = relationship(
        "GoalAuditResultORM",
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="GoalAuditResultORM.created_at.asc()",
    )

    def __repr__(self) -> str:
        """Return concise goal identity for diagnostics."""

        return f"GoalORM(id={self.id!s}, status={self.status.value!r}, iteration={self.current_iteration})"


class GoalAuditResultORM(Base, TimestampMixin):
    """Stored auditor verdict for each goal iteration."""

    __tablename__ = "goal_audit_results"
    __tenant_scoped__ = True

    goal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="")
    remaining_work_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    goal: Mapped[GoalORM] = relationship("GoalORM", back_populates="audits")

    def __repr__(self) -> str:
        """Return concise audit-row diagnostics."""

        return (
            f"GoalAuditResultORM(id={self.id!s}, goal_id={self.goal_id!s}, "
            f"iteration={self.iteration}, done={self.is_done})"
        )


__all__ = ["GoalORM", "GoalAuditResultORM", "GoalStatusORM"]
