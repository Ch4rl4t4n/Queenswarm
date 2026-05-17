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
        payload={"source": "self-service"},
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

