"""Unit coverage for Celery inspect helper."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.celery_health import inspect_celery_workers


def test_inspect_celery_workers_counts_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    inspector = MagicMock()
    inspector.ping.return_value = {"worker-a": {"ok": "pong"}}
    inspector.active.return_value = {"worker-a": [{"id": "1"}, {"id": "2"}]}
    inspector.reserved.return_value = {"worker-a": [{"id": "3"}]}

    monkeypatch.setattr(
        "app.core.celery_health.celery_app.control.inspect",
        lambda timeout=1.5: inspector,
    )

    snapshot = inspect_celery_workers()
    assert snapshot["ok"] is True
    assert snapshot["workers_up"] == 1
    assert snapshot["active_tasks"] == 2
    assert snapshot["reserved_tasks"] == 1


def test_inspect_celery_workers_handles_missing_inspector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.core.celery_health.celery_app.control.inspect",
        lambda timeout=1.5: None,
    )
    snapshot = inspect_celery_workers()
    assert snapshot["ok"] is False
    assert snapshot["workers_up"] == 0
