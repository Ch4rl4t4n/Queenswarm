"""Domain models for Queen `/goal` orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import uuid


class GoalStatus(StrEnum):
    """Lifecycle status for one high-level user goal."""

    PENDING = "pending"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    AUDITING = "auditing"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED_BY_BUDGET = "halted_by_budget"
    HALTED_BY_HUMAN = "halted_by_human"


@dataclass(slots=True)
class Goal:
    """Tenant-scoped high-level objective managed by the Queen."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    description_md: str
    acceptance_criteria_md: str
    max_iterations: int
    budget_usd: float
    status: GoalStatus
    current_iteration: int
    root_task_id: uuid.UUID | None
    created_at: datetime
    completed_at: datetime | None

    def __repr__(self) -> str:
        """Return concise debug identity."""

        return (
            f"Goal(id={self.id!s}, tenant_id={self.tenant_id!s}, "
            f"status={self.status.value!r}, iteration={self.current_iteration})"
        )


@dataclass(slots=True)
class GoalAuditResult:
    """Auditor verdict for one goal iteration."""

    iteration: int
    is_done: bool
    reasoning: str
    remaining_work_md: str
    confidence: float

    def __repr__(self) -> str:
        """Return concise audit result summary."""

        return (
            "GoalAuditResult("
            f"iteration={self.iteration}, is_done={self.is_done}, confidence={self.confidence:.2f})"
        )


__all__ = ["Goal", "GoalAuditResult", "GoalStatus"]
