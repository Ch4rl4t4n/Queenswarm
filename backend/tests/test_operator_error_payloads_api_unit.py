"""API tests for normalized operator error payloads."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import (
    dashboard_admin_wall,
    get_db,
    require_dashboard_session,
    require_dashboard_user_with_tenant_role,
)


@pytest.fixture
def clear_overrides() -> None:
    """Reset FastAPI dependency overrides after each test."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_settings_team_audit_logs_forbidden_payload_shape(clear_overrides: None) -> None:
    """Team endpoints return structured 403 payload when role lacks permission."""

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": MagicMock(id=uuid.uuid4()),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "member",
        "permissions": [],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/settings/team/audit-logs", headers={"Authorization": "Bearer x"})

    assert res.status_code == 403
    detail = res.json()["detail"]
    assert detail["code"] == "team_management_permission_required"
    assert detail["message"] == "Team management permission required."


@pytest.mark.asyncio
async def test_queen_maintainer_pr_draft_422_payload_shape(clear_overrides: None) -> None:
    """Maintainer denylist failures return code/message/details payload."""

    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["settings:view"],
        "user": MagicMock(id=actor_id),
    }

    with patch(
        "app.presentation.api.routers.queen_maintainer.validate_changed_paths",
        return_value=(False, [".env"]),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/queen-maintainer/pr-draft",
                headers={"Authorization": "Bearer x"},
                json={
                    "title": "fix: maintain guardrail",
                    "body": "Keep denylist safe with explicit checks.",
                    "slug": "denylist-guard",
                    "changed_paths": [".env"],
                },
            )

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "maintainer_denylist_blocked"
    assert detail["message"] == "Maintainer denylist blocked one or more paths."
    assert detail["details"]["blocked_paths"] == [".env"]


@pytest.mark.asyncio
async def test_admin_accounts_bulk_empty_patch_has_normalized_422(clear_overrides: None) -> None:
    """Admin bulk patch rejects empty mutation body with structured 422 payload."""

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dashboard:{uuid.uuid4()}"}
    app.dependency_overrides[dashboard_admin_wall] = lambda: True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/accounts/bulk",
            headers={"Authorization": "Bearer x"},
            json={"user_ids": [str(uuid.uuid4())]},
        )

    assert res.status_code == 422
    detail = res.json()["detail"]
    assert detail["code"] == "admin_accounts_patch_empty"
    assert detail["message"] == "No patch fields provided."

