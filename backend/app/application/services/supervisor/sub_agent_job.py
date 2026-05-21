"""Celery job telemetry for durable supervisor sub-agent steps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.worker.celery_app import celery_app

SUPERVISOR_SUB_AGENT_TASK_NAME = "hive.supervisor_sub_agent_step"


def extract_celery_task_id(short_memory: dict[str, Any] | None) -> str | None:
    """Return Celery task id persisted on a sub-agent row."""

    raw = (short_memory or {}).get("celery_task_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def extract_self_heal_attempts(short_memory: dict[str, Any] | None) -> int | None:
    """Return self-heal retry count from sub-agent short memory."""

    raw = (short_memory or {}).get("self_heal_attempts")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    return None


def parse_enqueued_at(short_memory: dict[str, Any] | None) -> datetime | None:
    """Parse Celery enqueue timestamp stored in short memory."""

    raw = (short_memory or {}).get("celery_enqueued_at")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def extract_requeue_count(short_memory: dict[str, Any] | None) -> int | None:
    """Return operator/Celery requeue counter from sub-agent short memory."""

    raw = (short_memory or {}).get("requeue_count")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    return None


@dataclass(frozen=True, slots=True)
class SubAgentJobSnapshot:
    """Resolved Celery AsyncResult view for one durable sub-agent step."""

    celery_task_id: str | None
    task_name: str
    state: str
    ready: bool
    successful: bool | None
    result: dict[str, Any] | None
    error: str | None
    enqueued_at: datetime | None
    self_heal_attempts: int | None


def build_sub_agent_job_snapshot(
    *,
    short_memory: dict[str, Any] | None,
    celery_task_id: str | None = None,
) -> SubAgentJobSnapshot:
    """Resolve Celery result backend state for one sub-agent durable job."""

    task_id = celery_task_id or extract_celery_task_id(short_memory)
    enqueued_at = parse_enqueued_at(short_memory)
    self_heal = extract_self_heal_attempts(short_memory)

    if not task_id:
        return SubAgentJobSnapshot(
            celery_task_id=None,
            task_name=SUPERVISOR_SUB_AGENT_TASK_NAME,
            state="NOT_ENQUEUED",
            ready=False,
            successful=None,
            result=None,
            error=None,
            enqueued_at=enqueued_at,
            self_heal_attempts=self_heal,
        )

    async_result = celery_app.AsyncResult(task_id)
    state = str(async_result.state or "PENDING")
    ready = bool(async_result.ready())
    successful: bool | None = async_result.successful() if ready else None
    result: dict[str, Any] | None = None
    error: str | None = None

    if successful is True:
        raw = async_result.result
        if isinstance(raw, dict):
            result = raw
        elif raw is not None:
            error = f"Unexpected result payload type: {type(raw).__name__}"
    elif successful is False:
        try:
            maybe_exc = async_result.result
            error = repr(maybe_exc) if maybe_exc is not None else "Celery reported failure without details."
        except Exception as exc:  # noqa: BLE001 — surface broker oddities to operators
            error = f"Could not read failure payload: {exc!s}"

    return SubAgentJobSnapshot(
        celery_task_id=task_id,
        task_name=SUPERVISOR_SUB_AGENT_TASK_NAME,
        state=state,
        ready=ready,
        successful=successful,
        result=result,
        error=error,
        enqueued_at=enqueued_at,
        self_heal_attempts=self_heal,
    )


__all__ = [
    "SUPERVISOR_SUB_AGENT_TASK_NAME",
    "SubAgentJobSnapshot",
    "build_sub_agent_job_snapshot",
    "extract_celery_task_id",
    "extract_requeue_count",
    "extract_self_heal_attempts",
    "parse_enqueued_at",
]
