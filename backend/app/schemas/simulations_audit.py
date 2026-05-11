"""HTTP projections for Postgres simulation audit ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SimulationResult


class SimulationAuditItem(BaseModel):
    """Operator-facing slice of swarm-linked simulation bookkeeping."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID | None = None
    result_type: SimulationResult
    confidence_pct: float
    scenario: dict[str, Any]
    docker_container_id: str | None = None
    created_at: datetime
    updated_at: datetime


__all__ = ["SimulationAuditItem"]
