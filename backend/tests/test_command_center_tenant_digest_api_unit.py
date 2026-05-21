"""ASGI tests for command-center per-tenant digest send."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, get_db


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset FastAPI overrides between test cases."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_command_center_send_tenant_digest_when_admin_then_delegates(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Platform admin can trigger one tenant digest from command center."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, status="active", name="Acme Hive")
    calls = {"send": 0, "invalidate": 0}

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            return tenant if key == tenant_id else None

        yield SimpleNamespace(get=_get)

    async def _fake_send(*_args, **_kwargs):  # noqa: ANN002, ANN003
        calls["send"] += 1
        return {
            "tenant_id": str(tenant_id),
            "sent": True,
            "sent_count": 1,
            "slack_sent": False,
            "discord_sent": False,
            "teams_sent": False,
            "action_count": 4,
            "recipients": ["ops@acme.com"],
        }

    async def _fake_invalidate(**_kwargs) -> int:  # noqa: ANN003
        calls["invalidate"] += 1
        return 2

    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest.send_supervisor_audit_digest_for_tenant",
        _fake_send,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.invalidate_supervisor_audit_rollup_cache",
        _fake_invalidate,
    )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[dashboard_admin_wall] = lambda: True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/operator/command-center/audit-digest-rollup/tenants/{tenant_id}/send-digest",
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["sent"] is True
    assert body["action_count"] == 4
    assert calls["send"] == 1
    assert calls["invalidate"] == 1


@pytest.mark.asyncio
async def test_command_center_send_tenant_digest_when_missing_then_404(
    restore_app_overrides: None,
) -> None:
    """Unknown tenant id returns 404."""

    tenant_id = uuid.uuid4()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            del _model, key
            return None

        yield SimpleNamespace(get=_get)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[dashboard_admin_wall] = lambda: True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/operator/command-center/audit-digest-rollup/tenants/{tenant_id}/send-digest",
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_command_center_send_attention_digests_when_alerts_then_batch(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Platform admin can batch-send digests for stale/never-sent tenants."""

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def _fake_batch(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return {
            "sent": True,
            "tenants_attempted": 2,
            "tenants_sent": 2,
            "digest_stale_count": 1,
            "digest_never_sent_count": 1,
        }

    monkeypatch.setattr(
        "app.application.services.supervisor.session_audit_digest_rollup.send_attention_supervisor_audit_digests",
        _fake_batch,
    )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[dashboard_admin_wall] = lambda: True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/command-center/audit-digest-rollup/send-attention-digests",
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["sent"] is True
    assert body["tenants_sent"] == 2
