"""ASGI tests for tenant audit log listing endpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset FastAPI overrides between test cases."""

    yield
    app.dependency_overrides.clear()


class _FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


@pytest.mark.asyncio
async def test_settings_team_audit_logs_when_owner_returns_rows(restore_app_overrides: None) -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    row = SimpleNamespace(
        id=uuid.uuid4(),
        action="password_changed",
        target_type="dashboard_user",
        target_ref=str(actor_id),
        actor_user_id=actor_id,
        payload={"source": "self-service", "ip": "10.0.0.42"},
        created_at=datetime.now(tz=UTC),
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalars(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return _FakeScalarResult([row])

        yield SimpleNamespace(scalars=_scalars)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=actor_id),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:test"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/settings/team/audit-logs", headers={"Authorization": "Bearer x"})

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 1
    assert body[0]["action"] == "password_changed"
    assert body[0]["payload"]["ip"] == "10.0.0.42"


@pytest.mark.asyncio
async def test_settings_team_audit_digest_config_get_and_patch(restore_app_overrides: None) -> None:
    """Owner can read and update tenant digest schedule config."""

    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={},
        name="Acme",
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            if key == tenant_id:
                return tenant
            return None

        async def _commit() -> None:
            return None

        async def _refresh(_obj: object) -> None:
            return None

        session = SimpleNamespace(
            get=_get,
            commit=_commit,
            refresh=_refresh,
        )
        yield session

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=actor_id),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:test"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_res = await client.get(
            "/api/v1/settings/team/audit-digest/config",
            headers={"Authorization": "Bearer x"},
        )
        assert get_res.status_code == 200
        assert "window_hours" in get_res.json()

        patch_res = await client.patch(
            "/api/v1/settings/team/audit-digest/config",
            headers={"Authorization": "Bearer x"},
            json={
                "enabled": True,
                "window_hours": 12,
                "schedule_hour_utc": 8,
                "extra_recipients": ["ops@acme.com"],
            },
        )

    assert patch_res.status_code == 200
    body = patch_res.json()
    assert body["window_hours"] == 12
    assert body["schedule_hour_utc"] == 8
    assert body["extra_recipients"] == ["ops@acme.com"]
    bucket = tenant.operator_settings["supervisor_audit_digest"]
    assert bucket["window_hours"] == 12


@pytest.mark.asyncio
async def test_settings_team_session_playbook_config_get_and_patch(restore_app_overrides: None) -> None:
    """Owner can read and update tenant session playbook automation config."""

    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={},
        name="Acme",
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            if key == tenant_id:
                return tenant
            return None

        async def _commit() -> None:
            return None

        async def _refresh(_obj: object) -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit, refresh=_refresh)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=actor_id),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:test"},
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_res = await client.get(
            "/api/v1/settings/team/session-playbook/config",
            headers={"Authorization": "Bearer x"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["auto_save_on_approve"] is False

        patch_res = await client.patch(
            "/api/v1/settings/team/session-playbook/config",
            headers={"Authorization": "Bearer x"},
            json={"auto_save_on_approve": True, "mark_verified_on_auto_save": False},
        )

    assert patch_res.status_code == 200
    body = patch_res.json()
    assert body["auto_save_on_approve"] is True
    assert body["mark_verified_on_auto_save"] is False
    bucket = tenant.operator_settings["supervisor_session_playbook"]
    assert bucket["auto_save_on_approve"] is True

