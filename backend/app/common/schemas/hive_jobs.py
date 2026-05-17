"""HTTP contracts for Celery-backed hive async jobs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

CeleryJobState = Literal[
    "PENDING",
    "STARTED",
    "SUCCESS",
    "FAILURE",
    "RETRY",
    "REVOKED",
]


class HivePostgresLedgerBrief(BaseModel):
    """Compact audit row backing ``hive_async_workflow_runs``."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    swarm_id: uuid.UUID
    workflow_id: uuid.UUID
    hive_task_id: uuid.UUID | None = None
    lifecycle: str
    created_at: datetime
    updated_at: datetime
    finished_at: datetime | None = None
    error_preview: str | None = Field(
        default=None,
        description="First line of stored failure text (full text lives in Postgres).",
    )


class HiveAsyncJobStatusResponse(BaseModel):
    """Snapshot of a deferred workflow run as seen by Celery + optional Postgres ledger."""

    model_config = ConfigDict(extra="ignore")

    celery_task_id: str
    state: CeleryJobState | str = Field(
        description="Upstream Celery state (uppercase) surfaced verbatim for dashboards.",
    )
    ready: bool = Field(description="Whether Celery considers the invocation terminal.")
    successful: bool | None = Field(
        default=None,
        description="True when SUCCESS; False on FAILURE; null while in-flight.",
    )
    workflow_result: dict[str, Any] | None = Field(
        default=None,
        description="Frozen :class:`RunWorkflowOnSwarmResponse` dump when SUCCESS.",
    )
    error: str | None = Field(default=None, description="Failure reason when FAILURE/REVOKED.")
    postgres_ledger: HivePostgresLedgerBrief | None = Field(
        default=None,
        description="Authoritative audit snapshot when the API row exists.",
    )


__all__ = ["CeleryJobState", "HiveAsyncJobStatusResponse", "HivePostgresLedgerBrief"]
