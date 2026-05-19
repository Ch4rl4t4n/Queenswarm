"""Pydantic contracts for operator pending-review queue."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.persistence.models.enums import PendingReviewStatus


class PendingReviewItemRow(BaseModel):
    """Serialized pending-review row for dashboards."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID | None
    swarm_id: uuid.UUID
    workflow_id: uuid.UUID
    simulation_id: uuid.UUID | None
    status: PendingReviewStatus
    reason: str
    confidence_fraction: float | None
    verification_passed: bool
    verification_notes: str | None
    step_summary: dict[str, Any] | None
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_note: str | None


class PendingReviewStats(BaseModel):
    """Aggregate counts for navigation badges."""

    pending_count: int = Field(ge=0)
    approved_count: int = Field(ge=0)
    rejected_count: int = Field(ge=0)


class PendingReviewResolveRequest(BaseModel):
    """Operator decision on a queued outcome."""

    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=4000)


__all__ = ["PendingReviewItemRow", "PendingReviewResolveRequest", "PendingReviewStats"]
