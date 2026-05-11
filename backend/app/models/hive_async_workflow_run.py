"""Celery-deferred swarm workflow bookkeeping for audit dashboards."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum as SQEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import HiveAsyncRunLifecycle

if TYPE_CHECKING:
    from app.models.swarm import SubSwarm
    from app.models.task import Task
    from app.models.workflow import Workflow


class HiveAsyncWorkflowRun(Base, TimestampMixin):
    """Postgres-backed mirror for ``defer_to_worker`` executions (immutable Celery IDs)."""

    __tablename__ = "hive_async_workflow_runs"

    celery_task_id: Mapped[str] = mapped_column(String(96), nullable=False, unique=True, index=True)
    swarm_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sub_swarms.id", ondelete="RESTRICT"),
        nullable=False,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="RESTRICT"),
        nullable=False,
    )
    hive_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_subject: Mapped[str | None] = mapped_column(String(512), nullable=True)

    lifecycle: Mapped[HiveAsyncRunLifecycle] = mapped_column(
        SQEnum(
            HiveAsyncRunLifecycle,
            values_callable=lambda obj: [m.value for m in obj],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        default=HiveAsyncRunLifecycle.QUEUED,
    )
    result_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    swarm: Mapped["SubSwarm"] = relationship(back_populates="async_workflow_runs")
    workflow: Mapped["Workflow"] = relationship(back_populates="async_workflow_runs")
    hive_task: Mapped["Task | None"] = relationship(back_populates="async_workflow_runs")

    def __repr__(self) -> str:
        """Concise celery join key for telemetry."""

        return (
            f"HiveAsyncWorkflowRun(celery_task_id={self.celery_task_id!r}, "
            f"lifecycle={self.lifecycle.value!r})"
        )
