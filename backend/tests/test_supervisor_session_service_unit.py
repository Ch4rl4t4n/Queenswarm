"""Unit tests for supervisor runtime policy helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_service import (
    apply_session_control,
    apply_session_review,
    coerce_runtime_mode,
    create_supervisor_session,
    enqueue_durable_sub_agent_step,
    normalize_roles,
    requeue_durable_sub_agents_after_approval,
    requeue_durable_sub_agents_on_resume,
    retry_sub_agent_step,
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


@pytest.mark.asyncio
async def test_requeue_durable_sub_agents_after_approval_when_needs_input_then_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approve flow re-enqueues durable sub-agents blocked on operator input."""

    sent: list[dict[str, object]] = []

    class _FakeAsyncResult:
        id = "celery-task-requeue-1"

    async def _fake_enqueue(*args, **kwargs):  # noqa: ANN002, ANN003
        del args
        sent.append(kwargs)
        sub = kwargs["sub_agent"]
        sub.status = "queued"
        return "celery-task-requeue-1"

    db = SimpleNamespace(
        flush=lambda: None,
        scalars=lambda *_args, **_kwargs: None,
    )

    async def _flush() -> None:
        return None

    db.flush = _flush

    sub = SimpleNamespace(
        id="sub-1",
        role="coder",
        status="needs_input",
        short_memory={},
        error_text="Awaiting approval",
    )
    session = SimpleNamespace(id="sess-1", runtime_mode="durable", sub_agents=[sub])

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.enqueue_durable_sub_agent_step",
        _fake_enqueue,
    )
    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)

    count = await requeue_durable_sub_agents_after_approval(db, session_row=session)  # type: ignore[arg-type]
    assert count == 1
    assert sent[0]["reason"] == "operator_approved"


@pytest.mark.asyncio
async def test_apply_session_review_when_approve_durable_then_requeues(monkeypatch: pytest.MonkeyPatch) -> None:
    """Session approve persists requeue metadata for durable runtime."""

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    async def _fake_requeue(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return 2

    async def _fake_resume(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return 0

    db = SimpleNamespace(flush=lambda: None)

    async def _flush() -> None:
        return None

    db.flush = _flush
    row = SimpleNamespace(
        status="needs_input",
        runtime_mode="durable",
        context_summary={
            "approval_required": True,
            "approval_reason": "Critical action keyword detected: drop",
        },
        sub_agents=[],
    )

    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.requeue_durable_sub_agents_after_approval",
        _fake_requeue,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.resume_inprocess_sub_agents_after_approval",
        _fake_resume,
    )

    await apply_session_review(db, session_row=row, decision="approve", note="Looks good")
    assert row.status == "running"
    assert row.context_summary["requeued_sub_agents"] == 2
    assert "approval_required" not in row.context_summary
    assert "approval_reason" not in row.context_summary


@pytest.mark.asyncio
async def test_requeue_durable_sub_agents_on_resume_when_queued_then_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume flow re-enqueues durable sub-agents still waiting in queue."""

    sent: list[str] = []

    async def _fake_enqueue(*args, **kwargs):  # noqa: ANN002, ANN003
        del args
        sub = kwargs["sub_agent"]
        sent.append(str(sub.role))
        return "celery-task-resume-1"

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    db = SimpleNamespace(flush=lambda: None)
    subs = [
        SimpleNamespace(id="1", role="researcher", status="queued", short_memory={}),
        SimpleNamespace(id="2", role="critic", status="completed", short_memory={}),
        SimpleNamespace(id="3", role="coder", status="pending", short_memory={}),
    ]
    session = SimpleNamespace(id="sess-1", runtime_mode="durable", sub_agents=subs)

    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.enqueue_durable_sub_agent_step",
        _fake_enqueue,
    )
    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)

    count = await requeue_durable_sub_agents_on_resume(db, session_row=session)  # type: ignore[arg-type]
    assert count == 2
    assert sent == ["researcher", "coder"]


@pytest.mark.asyncio
async def test_apply_session_control_when_resume_durable_then_requeues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Session resume persists requeue metadata for paused durable runtime."""

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    async def _fake_requeue(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return 3

    db = SimpleNamespace()

    async def _flush() -> None:
        return None

    db.flush = _flush
    row = SimpleNamespace(status="paused", runtime_mode="durable", context_summary={})

    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.requeue_durable_sub_agents_on_resume",
        _fake_requeue,
    )

    await apply_session_control(db, session_row=row, action="resume")  # type: ignore[arg-type]
    assert row.status == "running"
    assert row.context_summary["requeued_sub_agents"] == 3


@pytest.mark.asyncio
async def test_retry_sub_agent_step_when_durable_needs_input_then_requeues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Individual retry enqueues one durable sub-agent without full session approve."""

    async def _fake_enqueue(*args, **kwargs):  # noqa: ANN002, ANN003
        del args
        sub = kwargs["sub_agent"]
        assert kwargs["reason"] == "operator_retry"
        sub.status = "queued"
        return "celery-retry-1"

    db = SimpleNamespace()

    async def _flush() -> None:
        return None

    db.flush = _flush
    sub = SimpleNamespace(id="sub-1", role="coder", status="needs_input", short_memory={})
    session = SimpleNamespace(id="sess-1", runtime_mode="durable", status="needs_input", sub_agents=[sub])

    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.enqueue_durable_sub_agent_step",
        _fake_enqueue,
    )

    updated = await retry_sub_agent_step(db, session_row=session, sub_agent=sub)  # type: ignore[arg-type]
    assert updated.status == "queued"
    assert session.status == "running"

