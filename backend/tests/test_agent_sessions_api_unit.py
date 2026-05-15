"""ASGI tests for /api/v1/agents/sessions routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session
from app.presentation.api.routers import agent_sessions as agent_sessions_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset DI overrides between tests."""

    yield
    app.dependency_overrides.clear()


def _mk_sub(role: str) -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        role=role,
        status="completed",
        runtime_mode="inprocess",
        toolset=["analyze"],
        short_memory={},
        spawn_order=0,
        started_at=now,
        completed_at=now,
        last_output=f"{role} output",
        error_text=None,
    )


def _mk_session() -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        goal="Investigate onboarding drop-off",
        status="completed",
        runtime_mode="inprocess",
        created_by_subject="dash:test",
        context_summary={"requested_roles": ["researcher"]},
        swarm_id=None,
        task_id=None,
        started_at=now,
        completed_at=now,
        error_text=None,
        created_at=now,
        updated_at=now,
        sub_agents=[_mk_sub("researcher")],
    )


def _mk_routine() -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="daily-monitoring",
        goal_template="Generate daily monitoring summary",
        schedule_kind="interval",
        interval_seconds=3600,
        cron_expr=None,
        runtime_mode="durable",
        roles=["researcher", "critic"],
        retrieval_contract="policy+last_3_tasks",
        skills=["context", "diagnose"],
        context_payload={},
        status="scheduled",
        is_active=True,
        created_by_subject="dash:test",
        last_run_at=None,
        next_run_at=now,
        last_error=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_agent_sessions_create_when_enabled_returns_201(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create endpoint returns created session payload."""

    fake_row = _mk_session()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_create(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return fake_row

    async def _fake_get(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return fake_row

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    monkeypatch.setattr(settings, "supervisor_dynamic_subagents_enabled", True)
    monkeypatch.setattr(agent_sessions_router, "create_supervisor_session", _fake_create)
    monkeypatch.setattr(agent_sessions_router, "get_supervisor_session", _fake_get)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/agents/sessions",
            headers={"Authorization": "Bearer x"},
            json={"goal": "Investigate onboarding drop-off", "runtime_mode": "inprocess"},
        )
    assert res.status_code == 201
    body = res.json()
    assert body["goal"] == "Investigate onboarding drop-off"
    assert body["sub_agents"][0]["role"] == "researcher"


@pytest.mark.asyncio
async def test_agent_sessions_roles_returns_defaults(restore_app_overrides: None) -> None:
    """Roles metadata endpoint exposes supported role slugs."""

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/agents/sessions/meta/roles",
            headers={"Authorization": "Bearer x"},
        )
    assert res.status_code == 200
    assert "researcher" in res.json()


@pytest.mark.asyncio
async def test_agent_sessions_list_resolves_static_route_before_agent_id(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``/agents/sessions`` must resolve list route (not ``/agents/{agent_id}``)."""

    fake_row = _mk_session()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [fake_row]

    async def _fake_get(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return fake_row

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    monkeypatch.setattr(agent_sessions_router, "list_supervisor_sessions", _fake_list)
    monkeypatch.setattr(agent_sessions_router, "get_supervisor_session", _fake_get)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/agents/sessions?limit=40",
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 200
    payload = res.json()
    assert isinstance(payload, list)
    assert payload and payload[0]["id"] == str(fake_row.id)


@pytest.mark.asyncio
async def test_agent_sessions_review_when_enabled_returns_200(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review endpoint should return updated session payload."""

    fake_row = _mk_session()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_get(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return fake_row

    async def _fake_review(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return fake_row

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    monkeypatch.setattr(settings, "light_control_plane_enabled", True)
    monkeypatch.setattr(agent_sessions_router, "get_supervisor_session", _fake_get)
    monkeypatch.setattr(agent_sessions_router, "apply_session_review", _fake_review)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/agents/sessions/{fake_row.id}/review",
            headers={"Authorization": "Bearer x"},
            json={"decision": "approve"},
        )
    assert res.status_code == 200
    assert res.json()["id"] == str(fake_row.id)


@pytest.mark.asyncio
async def test_agent_routines_list_when_disabled_returns_empty(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routines list should be empty when feature flag is off."""

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    monkeypatch.setattr(settings, "routines_enabled", False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/agents/routines", headers={"Authorization": "Bearer x"})
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_agent_routines_create_when_enabled_returns_201(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routine create endpoint returns serialized routine payload."""

    fake_row = _mk_routine()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_create(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return fake_row

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    monkeypatch.setattr(settings, "routines_enabled", True)
    monkeypatch.setattr(agent_sessions_router, "create_supervisor_routine", _fake_create)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/agents/routines",
            headers={"Authorization": "Bearer x"},
            json={
                "name": "daily-monitoring",
                "goal_template": "Generate daily monitoring summary",
                "schedule_kind": "interval",
                "interval_seconds": 3600,
                "runtime_mode": "durable",
                "roles": ["researcher", "critic"],
            },
        )
    assert res.status_code == 201
    assert res.json()["name"] == "daily-monitoring"


@pytest.mark.asyncio
async def test_agent_routine_trigger_when_enabled_returns_session_id(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routine trigger endpoint returns spawned session id."""

    fake_routine = _mk_routine()
    created_session_id = uuid.uuid4()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        async def _scalar(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return fake_routine

        yield SimpleNamespace(commit=_commit, scalar=_scalar)

    async def _fake_trigger(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return created_session_id

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:test"}
    monkeypatch.setattr(settings, "routines_enabled", True)
    monkeypatch.setattr(agent_sessions_router, "trigger_supervisor_routine_now", _fake_trigger)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/agents/routines/{fake_routine.id}/trigger",
            headers={"Authorization": "Bearer x"},
        )
    assert res.status_code == 200
    assert res.json()["session_id"] == str(created_session_id)

