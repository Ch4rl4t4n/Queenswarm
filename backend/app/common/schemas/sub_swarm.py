"""Pydantic models for decentralized sub-swarm LangGraph invocation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunWorkflowOnSwarmRequest(BaseModel):
    """Operator payload for pinning optional task lineage + hive task JSON."""

    model_config = ConfigDict(extra="ignore")

    task_id: uuid.UUID | None = Field(
        default=None,
        description="When set, validates assignment to ``swarm_id`` before stepping.",
    )
    payload: dict[str, Any] = Field(default_factory=dict, description="Forwarded into each bee step.")
    defer_to_worker: bool = Field(
        default=False,
        description="When true, enqueue Celery ``hive.run_sub_swarm_workflow`` and return 202 metadata.",
    )


class RunWorkflowOnSwarmQueuedResponse(BaseModel):
    """Metadata returned when LangGraph execution hands off to Celery workers."""

    model_config = ConfigDict(extra="ignore")

    swarm_id: uuid.UUID
    workflow_id: uuid.UUID
    task_id: uuid.UUID | None = None
    celery_task_id: str
    status: Literal["queued"] = "queued"
    poll_hint: str = Field(
        default="GET /api/v1/jobs/<celery_task_id> with the same bearer token.",
        description="Where operators poll Celery-backed completion metadata.",
    )


class RunWorkflowOnSwarmResponse(BaseModel):
    """Unified trace surfaced after executing the subgraph + waggle publish."""

    model_config = ConfigDict(extra="ignore")

    swarm_id: uuid.UUID
    workflow_id: uuid.UUID
    ok: bool
    error_code: str | None = None
    error_detail: str | None = None
    traces: list[str] = Field(default_factory=list)
    step_summaries: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Operator-safe projection; unverified raw results are redacted.",
    )
    internal_step_summaries: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Privileged echo of internal payloads when expose_raw_step_outputs is enabled.",
    )
    verification_passed: bool = False
    verification_notes: list[str] = Field(default_factory=list)
    global_sync_recommended: bool = False


class GlobalHiveSyncAck(BaseModel):
    """Confirmation emitted after stamping ``last_global_sync_at`` for a colony."""

    model_config = ConfigDict(extra="ignore")

    swarm_id: uuid.UUID
    last_global_sync_at: datetime


__all__ = [
    "GlobalHiveSyncAck",
    "RunWorkflowOnSwarmQueuedResponse",
    "RunWorkflowOnSwarmRequest",
    "RunWorkflowOnSwarmResponse",
]
