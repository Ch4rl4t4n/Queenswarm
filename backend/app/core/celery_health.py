"""Celery worker inspect helpers shared by readiness, metrics, and system status."""

from __future__ import annotations

from typing import Any, TypedDict

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


class CeleryInspectSnapshot(TypedDict):
    """Aggregated Celery control-plane telemetry."""

    ok: bool
    workers_up: int
    active_tasks: int
    reserved_tasks: int
    error: str


def _count_task_map(payload: dict[str, Any] | None) -> int:
    """Sum task lists nested in ``inspect()`` worker maps."""

    if not payload:
        return 0
    total = 0
    for tasks in payload.values():
        if isinstance(tasks, list):
            total += len(tasks)
        elif isinstance(tasks, dict):
            total += sum(len(v) for v in tasks.values() if isinstance(v, list))
    return total


def inspect_celery_workers(*, timeout: float = 1.5) -> CeleryInspectSnapshot:
    """Return worker liveness plus coarse queue pressure from Celery inspect API."""

    try:
        inspector = celery_app.control.inspect(timeout=timeout)
        if inspector is None:
            return {
                "ok": False,
                "workers_up": 0,
                "active_tasks": 0,
                "reserved_tasks": 0,
                "error": "inspect_unavailable",
            }
        ping = inspector.ping() or {}
        workers_up = len(ping)
        active = _count_task_map(inspector.active())
        reserved = _count_task_map(inspector.reserved())
        return {
            "ok": workers_up > 0,
            "workers_up": workers_up,
            "active_tasks": active,
            "reserved_tasks": reserved,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 — operator surfaces must survive broker blips
        logger.warning(
            "celery_health.inspect_failed",
            agent_id="celery_health",
            swarm_id="global",
            task_id="inspect",
            error=str(exc),
        )
        return {
            "ok": False,
            "workers_up": 0,
            "active_tasks": 0,
            "reserved_tasks": 0,
            "error": str(exc),
        }


__all__ = ["CeleryInspectSnapshot", "inspect_celery_workers"]
