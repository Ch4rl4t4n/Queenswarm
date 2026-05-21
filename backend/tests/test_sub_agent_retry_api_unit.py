"""ASGI tests for per sub-agent retry endpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import agent_sessions as sessions_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset DI overrides between tests."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sub_agent_retry_endpoint_when_ok_then_returns_sub_agent(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry endpoint returns updated sub-agent row."""

    session_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    sub = SimpleNamespace(
        id=sub_id,
        role="researcher",
        status="queued",
        runtime_mode="durable",
        toolset=[],
        short_memory={"celery_task_id": "new-task"},
        spawn_order=0,
        started_at=None,
        completed_at=None,
        last_output=None,
        error_text=None,
    )
    session = SimpleNamespace(id=session_id, sub_agents=[sub])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        async def _refresh(row: object) -> None:
            del row

        yield SimpleNamespace(commit=_commit, refresh=_refresh)

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_retry(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return sub

    async def _fake_audit(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": "dash:operator",
        "tenant_id": str(tenant_id),
    }
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "sub": "dash:operator",
        "tenant_id": tenant_id,
        "tenant_role": "owner",
    }
    monkeypatch.setattr(sessions_router, "get_supervisor_session", _fake_get_session)
    monkeypatch.setattr(sessions_router, "retry_sub_agent_step", _fake_retry)
    monkeypatch.setattr(sessions_router, "write_supervisor_session_audit_log", _fake_audit)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/agents/sessions/{session_id}/sub-agents/{sub_id}/retry")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(sub_id)
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_sub_agent_retry_endpoint_when_validation_fails_then_400(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry endpoint maps service validation errors to HTTP 400."""

    session_id = uuid.uuid4()
    sub_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    sub = SimpleNamespace(id=sub_id, role="researcher", status="failed", runtime_mode="durable")
    session = SimpleNamespace(id=session_id, sub_agents=[sub])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_retry(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise ValueError("Sub-agent step already completed.")

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": "dash:operator",
        "tenant_id": str(tenant_id),
    }
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "sub": "dash:operator",
        "tenant_id": tenant_id,
        "tenant_role": "owner",
    }
    monkeypatch.setattr(sessions_router, "get_supervisor_session", _fake_get_session)
    monkeypatch.setattr(sessions_router, "retry_sub_agent_step", _fake_retry)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(f"/api/v1/agents/sessions/{session_id}/sub-agents/{sub_id}/retry")

    assert response.status_code == 400
