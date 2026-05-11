"""Workflow graphs produced by the Auto Workflow Breaker (guarded steps + parallel groups)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum as SQEnum, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import AgentRole, StepStatus, WorkflowStatus


    """Breaker output: ordered steps, parallel groups, recipe recall metadata."""

    __tablename__ = "workflows"

    original_task_text: Mapped[str] = mapped_column(Text, nullable=False)
    decomposition_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        SQEnum(
            WorkflowStatus,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=WorkflowStatus.PENDING,
    )
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_steps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parallelizable_groups: Mapped[list[Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    matching_recipe_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recipes.id"),
        nullable=True,
    )
    estimated_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.step_order",
    )
    recipe: Mapped["Recipe | None"] = relationship(
        "Recipe",
        back_populates="matched_workflows",
        foreign_keys=[matching_recipe_id],
    )
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="workflow")

    def __repr__(self) -> str:
        """Return a concise debug representation of the workflow."""

        return (
            f"Workflow(id={self.id!s}, status={self.status.value!r}, "
            f"steps={self.completed_steps}/{self.total_steps})"
        )


class WorkflowStep(Base, TimestampMixin):
    """Atomic guardrailed step routed to a swarm role with evaluation rubric."""

    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_role: Mapped[AgentRole] = mapped_column(
        SQEnum(
            AgentRole,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=48,
        ),
        nullable=False,
    )
    status: Mapped[StepStatus] = mapped_column(
        SQEnum(
            StepStatus,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=StepStatus.PENDING,
    )
    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    output_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    guardrails: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    evaluation_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="steps")

    def __repr__(self) -> str:
        """Return a concise debug representation of the workflow step."""

        return (
            f"WorkflowStep(id={self.id!s}, order={self.step_order}, "
            f"role={self.agent_role.value!r})"
        )
