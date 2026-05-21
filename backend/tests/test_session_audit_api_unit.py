"""ASGI tests for supervisor session audit endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
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
async def test_session_audit_logs_endpoint_when_session_exists_then_returns_rows(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit list endpoint returns operator action rows for one session."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    session = SimpleNamespace(id=session_id, sub_agents=[])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [
            {
                "id": str(uuid.uuid4()),
                "tenant_id": str(tenant_id),
                "action": "supervisor_session_control",
                "target_type": "supervisor_session",
                "target_ref": str(session_id),
                "actor_user_id": str(uuid.uuid4()),
                "payload": {"control_action": "pause"},
                "created_at": datetime.now(tz=UTC),
            },
        ]

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
    monkeypatch.setattr(sessions_router, "list_supervisor_session_audit_logs", _fake_list)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/audit-logs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["action"] == "supervisor_session_control"


@pytest.mark.asyncio
async def test_session_audit_export_endpoint_when_csv_then_attachment(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit export endpoint returns CSV attachment."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    session = SimpleNamespace(id=session_id, sub_agents=[])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [
            {
                "id": "log-1",
                "tenant_id": str(tenant_id),
                "action": "supervisor_sub_agent_retry",
                "target_type": "supervisor_session",
                "target_ref": str(session_id),
                "actor_user_id": None,
                "payload": {"sub_agent_role": "coder"},
                "created_at": datetime.now(tz=UTC),
            },
        ]

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
    monkeypatch.setattr(sessions_router, "list_supervisor_session_audit_logs", _fake_list)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/agents/sessions/{session_id}/audit-logs/export?format=csv",
        )

    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "supervisor_sub_agent_retry" in response.text


@pytest.mark.asyncio
async def test_session_audit_export_endpoint_when_include_events_then_merged_json(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Merged export returns audit rows plus session timeline events."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    session = SimpleNamespace(id=session_id, sub_agents=[])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [
            {
                "id": "log-1",
                "tenant_id": str(tenant_id),
                "action": "supervisor_session_create",
                "target_type": "supervisor_session",
                "target_ref": str(session_id),
                "actor_user_id": None,
                "payload": {"runtime_mode": "durable"},
                "created_at": datetime.now(tz=UTC),
            },
        ]

    async def _fake_events(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                supervisor_session_id=session_id,
                sub_agent_session_id=None,
                event_type="session_started",
                level="info",
                message="Session started",
                payload={},
                occurred_at=datetime.now(tz=UTC),
                created_at=datetime.now(tz=UTC),
            ),
        ]

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
    monkeypatch.setattr(sessions_router, "list_supervisor_session_audit_logs", _fake_list)
    monkeypatch.setattr(sessions_router, "list_session_events", _fake_events)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/agents/sessions/{session_id}/audit-logs/export?format=json&include_events=true",
        )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == str(session_id)
    assert len(body["audit_logs"]) == 1
    assert len(body["session_events"]) == 1
    assert body["session_events"][0]["event_type"] == "session_started"


@pytest.mark.asyncio
async def test_session_interact_endpoint_when_ok_then_writes_audit(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interact endpoint appends timeline event and operator audit row."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    event_id = uuid.uuid4()
    session = SimpleNamespace(id=session_id, sub_agents=[])
    event = SimpleNamespace(
        id=event_id,
        supervisor_session_id=session_id,
        sub_agent_session_id=None,
        event_type="operator_interaction",
        level="info",
        message="Focus on checkout latency",
        payload={"kind": "operator_command"},
        occurred_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_interact(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return event

    audit_calls: list[dict[str, object]] = []

    async def _fake_audit(*args, **kwargs):  # noqa: ANN002, ANN003
        del args
        audit_calls.append(kwargs)

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
    monkeypatch.setattr(sessions_router, "append_operator_interaction", _fake_interact)
    monkeypatch.setattr(sessions_router, "write_supervisor_session_audit_log", _fake_audit)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/agents/sessions/{session_id}/interact",
            json={"command": "Focus on checkout latency"},
        )

    assert response.status_code == 200
    assert len(audit_calls) == 1
    assert audit_calls[0]["action"] == "supervisor_session_interact"
    assert audit_calls[0]["payload"]["event_id"] == str(event_id)


@pytest.mark.asyncio
async def test_session_context_history_endpoint_when_rows_exist_then_returns_diffs(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Context history endpoint returns control/review context diffs."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    session = SimpleNamespace(id=session_id, sub_agents=[])

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_history(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [
            {
                "audit_id": str(uuid.uuid4()),
                "action": "supervisor_session_control",
                "created_at": datetime.now(tz=UTC),
                "context_diff": {
                    "changed": {"requeued_sub_agents": {"before": 0, "after": 2}},
                },
                "session_status": "running",
                "control_action": "resume",
                "decision": None,
            },
        ]

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
    monkeypatch.setattr(sessions_router, "list_supervisor_session_context_history", _fake_history)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/context-history")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["control_action"] == "resume"
    assert body[0]["context_diff"]["changed"]["requeued_sub_agents"]["after"] == 2


@pytest.mark.asyncio
async def test_session_report_export_endpoint_when_html_then_attachment(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report export endpoint returns printable HTML attachment."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    session = SimpleNamespace(
        id=session_id,
        goal="Latency investigation",
        status="running",
        runtime_mode="durable",
        created_by_subject="dash:test",
        context_summary={},
        swarm_id=None,
        task_id=None,
        started_at=now,
        completed_at=None,
        error_text=None,
        created_at=now,
        updated_at=now,
        sub_agents=[],
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return []

    async def _fake_history(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return []

    async def _fake_events(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return []

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
    monkeypatch.setattr(sessions_router, "list_supervisor_session_audit_logs", _fake_list)
    monkeypatch.setattr(sessions_router, "list_supervisor_session_context_history", _fake_history)
    monkeypatch.setattr(sessions_router, "list_session_events", _fake_events)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/report/export?format=html")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Operator Session Report" in response.text


@pytest.mark.asyncio
async def test_session_report_export_endpoint_when_pdf_then_attachment(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Report export endpoint returns downloadable PDF attachment."""

    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    now = datetime.now(tz=UTC)
    session = SimpleNamespace(
        id=session_id,
        goal="Latency investigation",
        status="running",
        runtime_mode="durable",
        created_by_subject="dash:test",
        context_summary={},
        swarm_id=None,
        task_id=None,
        started_at=now,
        completed_at=None,
        error_text=None,
        created_at=now,
        updated_at=now,
        sub_agents=[],
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return []

    async def _fake_history(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return []

    async def _fake_events(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return []

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
    monkeypatch.setattr(sessions_router, "list_supervisor_session_audit_logs", _fake_list)
    monkeypatch.setattr(sessions_router, "list_supervisor_session_context_history", _fake_history)
    monkeypatch.setattr(sessions_router, "list_session_events", _fake_events)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/report/export?format=pdf")

    assert response.status_code == 200
    assert "application/pdf" in response.headers.get("content-type", "")
    assert response.content.startswith(b"%PDF")
