"""Unit tests for tenant-scoped memory dreaming Celery tasks."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.worker import dreaming_tasks


def test_run_memory_dreaming_uses_tenant_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Task should call DreamerService with the provided tenant id."""

    tenant_id = uuid.uuid4()
    captured: dict[str, object] = {}

    async def _lock_ok(_name: str, *, owner: str, ttl_sec: int) -> bool:
        captured["owner"] = owner
        captured["ttl_sec"] = ttl_sec
        return True

    async def _unlock(_name: str, *, owner: str) -> None:
        captured["released"] = owner

    class _FakeService:
        def __init__(self, **_kwargs: object) -> None:
            return None

        async def run_cycle(self, *, tenant_id: uuid.UUID, window_hours: int):  # noqa: ANN201
            captured["tenant_id"] = tenant_id
            captured["window_hours"] = window_hours
            return SimpleNamespace(
                id=uuid.uuid4(),
                status=SimpleNamespace(value="completed"),
                items_consolidated=4,
            )

    monkeypatch.setattr(dreaming_tasks, "try_acquire_distributed_lock", _lock_ok)
    monkeypatch.setattr(dreaming_tasks, "release_distributed_lock", _unlock)
    monkeypatch.setattr(dreaming_tasks, "DreamerService", _FakeService)
    async def _neo4j_driver() -> SimpleNamespace:
        return SimpleNamespace()

    monkeypatch.setattr(dreaming_tasks, "get_neo4j_driver", _neo4j_driver)

    result = dreaming_tasks.run_memory_dreaming.__wrapped__(str(tenant_id))

    assert result["status"] == "completed"
    assert result["tenant_id"] == str(tenant_id)
    assert captured["tenant_id"] == tenant_id
    assert int(captured["window_hours"]) >= 1


def test_dreaming_nightly_alias_delegates_to_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy task name should call the tenant scheduler task."""

    monkeypatch.setattr(dreaming_tasks, "schedule_memory_dreaming", lambda: {"queued": 3, "skipped": 1})
    result = dreaming_tasks.dreaming_nightly_cycle()
    assert result == {"queued": 3, "skipped": 1}
