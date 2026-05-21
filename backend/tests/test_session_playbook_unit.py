"""Unit tests for supervisor session → operator playbook conversion."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_playbook import (
    SessionPlaybookNotReadyError,
    SessionPlaybookNotVerifiedError,
    build_playbook_steps,
    map_supervisor_role_to_agent_role,
    save_supervisor_session_playbook,
    session_eligible_for_verified_playbook,
    suggest_playbook_name,
)
from app.infrastructure.persistence.models.enums import AgentRole


def _session(**overrides: object) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "goal": "Ship pricing page refresh with verified guardrails",
        "status": "completed",
        "runtime_mode": "durable",
        "context_summary": {"requested_roles": ["researcher", "critic"], "retrieval_contract": "policy"},
        "swarm_id": None,
        "task_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _sub(*, role: str, order: int, status: str = "completed", output: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        role=role,
        spawn_order=order,
        status=status,
        runtime_mode="durable",
        toolset=["browser"],
        short_memory={"self_heal_attempts": 0},
        last_output=output,
    )


def test_map_supervisor_role_to_agent_role() -> None:
    assert map_supervisor_role_to_agent_role("researcher") == AgentRole.SCRAPER
    assert map_supervisor_role_to_agent_role("critic") == AgentRole.EVALUATOR
    assert map_supervisor_role_to_agent_role("unknown") == AgentRole.REPORTER


def test_build_playbook_steps_includes_orchestrator_and_sub_agents() -> None:
    session = _session()
    steps = build_playbook_steps(
        session_row=session,
        sub_agents=[_sub(role="researcher", order=0), _sub(role="critic", order=1)],
    )
    assert len(steps) == 3
    assert steps[0]["agent_role"] == AgentRole.REPORTER.value
    assert steps[1]["guardrails"]["supervisor_role"] == "researcher"
    assert steps[2]["agent_role"] == AgentRole.EVALUATOR.value


def test_build_playbook_steps_requires_sub_agents() -> None:
    with pytest.raises(SessionPlaybookNotReadyError):
        build_playbook_steps(session_row=_session(), sub_agents=[])


def test_suggest_playbook_name_truncates_goal() -> None:
    sid = uuid.uuid4()
    name = suggest_playbook_name(goal="A" * 300, session_id=sid)
    assert name.startswith("playbook_")
    assert len(name) <= 200


def test_session_eligible_for_verified_playbook() -> None:
    completed = _session(status="completed")
    assert session_eligible_for_verified_playbook(completed) is True
    running = _session(status="running")
    running.sub_agents = [_sub(role="researcher", order=0, status="completed")]
    assert session_eligible_for_verified_playbook(running) is True


@pytest.mark.asyncio
async def test_save_supervisor_session_playbook_persists_recipe(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_create(_db, body, *, swarm_id: str = "", task_id: str = "") -> SimpleNamespace:
        captured["body"] = body
        captured["swarm_id"] = swarm_id
        return SimpleNamespace(id=uuid.uuid4(), name=body.name, verified_at=None)

    monkeypatch.setattr(
        "app.application.services.supervisor.session_playbook.create_recipe_entry",
        _fake_create,
    )
    session = _session()
    session.sub_agents = [_sub(role="researcher", order=0), _sub(role="critic", order=1)]
    recipe, meta = await save_supervisor_session_playbook(
        object(),  # type: ignore[arg-type]
        session_row=session,
        mark_verified=False,
    )
    body = captured["body"]
    assert body.workflow_template["source"] == "supervisor_session_playbook"
    assert len(body.workflow_template["steps"]) == 3
    assert meta["step_count"] == 3
    assert recipe.name == body.name


@pytest.mark.asyncio
async def test_maybe_auto_save_playbook_on_approve_when_enabled_then_persists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_playbook import maybe_auto_save_playbook_on_approve
    from app.core.config import settings

    session = _session(status="completed")
    session.sub_agents = [_sub(role="researcher", order=0), _sub(role="critic", order=1)]
    tenant = SimpleNamespace(
        operator_settings={"supervisor_session_playbook": {"auto_save_on_approve": True}},
    )
    monkeypatch.setattr(settings, "recipes_enabled", True)

    async def _fake_save(_db, *, session_row, **kwargs):  # noqa: ANN001, ANN003
        del _db, session_row, kwargs
        return SimpleNamespace(id=uuid.uuid4(), name="playbook_test"), {"step_count": 3, "verified": True}

    monkeypatch.setattr(
        "app.application.services.supervisor.session_playbook.save_supervisor_session_playbook",
        _fake_save,
    )

    class _FakeDb:
        async def flush(self) -> None:
            return None

    result = await maybe_auto_save_playbook_on_approve(_FakeDb(), tenant=tenant, session_row=session)  # type: ignore[arg-type]
    assert result is not None
    assert result["auto"] is True
    assert session.context_summary["playbook_recipe_id"]


@pytest.mark.asyncio
async def test_maybe_auto_save_playbook_on_approve_skips_when_already_saved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.supervisor.session_playbook import maybe_auto_save_playbook_on_approve
    from app.core.config import settings

    session = _session(status="completed")
    session.context_summary = {"playbook_recipe_id": str(uuid.uuid4())}
    tenant = SimpleNamespace(
        operator_settings={"supervisor_session_playbook": {"auto_save_on_approve": True}},
    )
    monkeypatch.setattr(settings, "recipes_enabled", True)

    result = await maybe_auto_save_playbook_on_approve(object(), tenant=tenant, session_row=session)  # type: ignore[arg-type]
    assert result is None


@pytest.mark.asyncio
async def test_save_supervisor_session_playbook_rejects_unverified_stamp() -> None:
    session = _session(status="running")
    session.sub_agents = [
        _sub(role="researcher", order=0, status="running"),
        _sub(role="critic", order=1, status="running"),
    ]
    with pytest.raises(SessionPlaybookNotVerifiedError):
        await save_supervisor_session_playbook(
            object(),  # type: ignore[arg-type]
            session_row=session,
            mark_verified=True,
        )
