"""Unit tests for supervisor runtime policy helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_service import (
    apply_session_review,
    coerce_runtime_mode,
    create_supervisor_session,
    normalize_roles,
)
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings


def test_normalize_roles_when_duplicates_and_invalid_then_filters() -> None:
    """Roles list keeps first valid unique values only."""

    out = normalize_roles(["Researcher", "coder", "coder", "unknown", "browser-operator"])
    assert out == ["researcher", "coder", "browser_operator"]


def test_normalize_roles_when_empty_then_falls_back() -> None:
    """Fallback roles are emitted for empty input."""

    assert normalize_roles([]) == ["researcher", "critic"]


def test_coerce_runtime_mode_when_durable_disabled_then_inprocess(monkeypatch) -> None:
    """Durable requests downgrade to inprocess when flag is off."""

    monkeypatch.setattr(settings, "supervisor_durable_mode_enabled", False)
    assert coerce_runtime_mode("durable") == "inprocess"


def test_coerce_runtime_mode_when_durable_enabled_then_kept(monkeypatch) -> None:
    """Durable mode remains durable when explicitly enabled."""

    monkeypatch.setattr(settings, "supervisor_durable_mode_enabled", True)
    assert coerce_runtime_mode("durable") == "durable"


@pytest.mark.asyncio
async def test_apply_session_review_when_reject_then_needs_input(monkeypatch) -> None:
    """Reject decisions move sessions into ``needs_input`` and persist approval state."""

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    db = SimpleNamespace(flush=lambda: None)

    async def _flush() -> None:
        return None

    db.flush = _flush
    row = SimpleNamespace(status="running", context_summary={})
    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)
    await apply_session_review(db, session_row=row, decision="reject", note="Need operator input")
    assert row.status == "needs_input"
    assert row.context_summary["approval_state"] == "reject"


@pytest.mark.asyncio
async def test_create_supervisor_session_when_sub_agent_needs_input_then_session_stays_open(monkeypatch) -> None:
    """In-process flow must not force-complete sessions waiting for operator input."""

    class _FakeDb:
        def add(self, _row: object) -> None:
            return None

        async def flush(self) -> None:
            return None

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    async def _run_sub(_db, *, supervisor_session, sub_agent, **kwargs):  # noqa: ANN001, ANN003
        del _db, kwargs
        supervisor_session.status = "needs_input"
        sub_agent.status = "needs_input"
        return None

    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)
    monkeypatch.setattr("app.application.services.supervisor.session_service.run_sub_agent_inprocess", _run_sub)
    monkeypatch.setattr(settings, "supervisor_skills_enabled", False)
    session_row = await create_supervisor_session(
        _FakeDb(),
        goal="Delete production key material safely",
        created_by_subject="tester",
        runtime_mode="inprocess",
        roles=["coder"],
        shared_context=SharedContextService(),
    )
    assert session_row.status == "needs_input"

