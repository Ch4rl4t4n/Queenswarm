"""Executable tasks tied to workflows, recipes, pollen, and sub-swarms."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SQEnum, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import TaskStatus, TaskType


class Task(Base, TimestampMixin):
    """Operational unit bridging agents, swarm context, breaker graphs, and recipes."""

    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    task_type: Mapped[TaskType] = mapped_column(
        SQEnum(
            TaskType,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=48,
        ),
        nullable=False,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SQEnum(
            TaskStatus,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=TaskStatus.PENDING,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    swarm_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sub_swarms.id"), nullable=True)
    workflow_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workflows.id"),
        nullable=True,
        index=True,
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"),
        nullable=True,
    )
    pollen_awarded: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recipe_used_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recipes.id"),
        nullable=True,
    )
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
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent: Mapped["Agent | None"] = relationship(
        "Agent",
        back_populates="tasks",
    )
    swarm: Mapped["SubSwarm | None"] = relationship(
        "SubSwarm",
        back_populates="tasks",
    )
    workflow: Mapped["Workflow | None"] = relationship(
        "Workflow",
        back_populates="tasks",
    )
    recipe_used: Mapped["Recipe | None"] = relationship(
        "Recipe",
        foreign_keys=[recipe_used_id],
    )

    def __repr__(self) -> str:
        """Return a concise debug representation of the task."""

        return (
            f"Task(id={self.id!s}, type={self.task_type.value!r}, "
            f"status={self.status.value!r})"
        )
