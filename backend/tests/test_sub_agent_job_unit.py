"""Unit tests for durable sub-agent Celery job telemetry."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.services.supervisor.sub_agent_job import (
    build_sub_agent_job_snapshot,
    extract_celery_task_id,
    extract_self_heal_attempts,
    parse_enqueued_at,
)


def test_extract_celery_task_id_when_present_then_returns_trimmed() -> None:
    """Task id helper reads durable enqueue metadata from short memory."""

    assert extract_celery_task_id({"celery_task_id": " abc-123 "}) == "abc-123"
    assert extract_celery_task_id({}) is None


def test_parse_enqueued_at_when_iso_string_then_parses() -> None:
    """Enqueue timestamp helper accepts ISO-8601 strings."""

    parsed = parse_enqueued_at({"celery_enqueued_at": "2026-05-19T12:00:00+00:00"})
    assert parsed is not None
    assert parsed.year == 2026


def test_extract_self_heal_attempts_when_numeric_then_returns_int() -> None:
    """Self-heal counter helper normalizes numeric short memory values."""

    assert extract_self_heal_attempts({"self_heal_attempts": 3}) == 3
    assert extract_self_heal_attempts({"self_heal_attempts": 2.0}) == 2


def test_build_sub_agent_job_snapshot_when_missing_task_id_then_not_enqueued(monkeypatch) -> None:
    """Missing Celery id yields NOT_ENQUEUED without touching the broker."""

    snapshot = build_sub_agent_job_snapshot(short_memory={})
    assert snapshot.state == "NOT_ENQUEUED"
    assert snapshot.celery_task_id is None
    assert snapshot.ready is False


def test_build_sub_agent_job_snapshot_when_success_then_maps_result(monkeypatch) -> None:
    """Successful AsyncResult payloads surface in the job snapshot."""

    class _FakeAsyncResult:
        def __init__(self, task_id: str) -> None:
            self.task_id = task_id

        @property
        def state(self) -> str:
            return "SUCCESS"

        def ready(self) -> bool:
            return True

        def successful(self) -> bool:
            return True

        @property
        def result(self) -> dict[str, str]:
            return {"ok": True, "sub_agent_session_id": "sub-1"}

    monkeypatch.setattr(
        "app.application.services.supervisor.sub_agent_job.celery_app.AsyncResult",
        _FakeAsyncResult,
    )

    snapshot = build_sub_agent_job_snapshot(
        short_memory={"celery_task_id": "task-99", "self_heal_attempts": 2},
    )
    assert snapshot.state == "SUCCESS"
    assert snapshot.successful is True
    assert snapshot.result == {"ok": True, "sub_agent_session_id": "sub-1"}
    assert snapshot.self_heal_attempts == 2
