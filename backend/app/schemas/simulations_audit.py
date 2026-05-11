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


class SimulationDetailItem(SimulationAuditItem):
    """Extended audit row including sandbox output excerpts."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    result_data: dict[str, Any] | None = None
    stdout: str | None = None
    stderr: str | None = None
    duration_sec: float | None = None


class SimulationCreateRequest(BaseModel):
    """Ingest a completed or in-flight Docker simulation record."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    task_id: uuid.UUID | None = Field(
        default=None,
        description="Optional linkage back to the hive backlog.",
    )
    scenario: dict[str, Any] = Field(default_factory=dict)
    result_type: SimulationResult
    confidence_pct: float = Field(ge=0.0, le=100.0)
    result_data: dict[str, Any] | None = None
    docker_container_id: str | None = Field(default=None, max_length=128)
    duration_sec: float | None = Field(default=None, ge=0.0, le=86_400.0)
    stdout: str | None = None
    stderr: str | None = None


__all__ = ["SimulationAuditItem", "SimulationCreateRequest", "SimulationDetailItem"]
