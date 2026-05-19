"""Unit coverage for observability bootstrap."""

from __future__ import annotations

import pytest

from app.core.observability import build_langfuse_metadata, configure_observability


def test_build_langfuse_metadata_includes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    meta = build_langfuse_metadata(
        agent_id="bee-1",
        task_id="task-9",
        swarm_id="swarm-2",
        workflow_id="wf-3",
    )
    assert meta["trace_user_id"] == "bee-1"
    assert meta["session_id"] == "task-9:swarm-2"
    assert "swarm:swarm-2" in meta["tags"]


def test_configure_observability_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.observability.settings.langfuse_enabled", False)
    monkeypatch.setattr("app.core.observability.settings.opentelemetry_enabled", False)
    configure_observability()
    configure_observability()
