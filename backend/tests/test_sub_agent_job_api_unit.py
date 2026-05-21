"""ASGI tests for sub-agent Celery job status endpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.supervisor.sub_agent_job import SubAgentJobSnapshot
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import agent_sessions as sessions_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset DI overrides between tests."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sub_agent_job_endpoint_when_sub_agent_exists_then_returns_snapshot(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Job endpoint returns Celery telemetry for one durable sub-agent."""

    session_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    sub = SimpleNamespace(
        id=sub_id,
        short_memory={"celery_task_id": "celery-task-1", "self_heal_attempts": 1},
    )
    session = SimpleNamespace(id=session_id, sub_agents=[sub])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    def _fake_snapshot(*, short_memory, celery_task_id=None):  # noqa: ANN001
        del celery_task_id
        return SubAgentJobSnapshot(
            celery_task_id=str(short_memory.get("celery_task_id")),
            task_name="hive.supervisor_sub_agent_step",
            state="SUCCESS",
            ready=True,
            successful=True,
            result={"ok": True},
            error=None,
            enqueued_at=None,
            self_heal_attempts=1,
        )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "sub": "dash:operator",
        "tenant_role": "owner",
    }
    monkeypatch.setattr(sessions_router, "get_supervisor_session", _fake_get_session)
    monkeypatch.setattr(sessions_router, "build_sub_agent_job_snapshot", _fake_snapshot)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/sub-agents/{sub_id}/job")

    assert response.status_code == 200
    body = response.json()
    assert body["celery_task_id"] == "celery-task-1"
    assert body["state"] == "SUCCESS"
    assert body["successful"] is True
    assert body["self_heal_attempts"] == 1


@pytest.mark.asyncio
async def test_sub_agent_job_endpoint_when_sub_agent_missing_then_404(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Job endpoint returns 404 when sub-agent id is unknown."""

    session_id = uuid.uuid4()
    session = SimpleNamespace(id=session_id, sub_agents=[])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "sub": "dash:operator",
        "tenant_role": "owner",
    }
    monkeypatch.setattr(sessions_router, "get_supervisor_session", _fake_get_session)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/sub-agents/{uuid.uuid4()}/job")

    assert response.status_code == 404
