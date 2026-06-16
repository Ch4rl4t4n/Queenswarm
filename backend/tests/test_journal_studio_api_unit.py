"""API unit tests for Track O TJ4 journal studio router."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _owner_principal() -> dict[str, object]:
    return {
        "user": type("U", (), {"id": uuid.uuid4()})(),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "sub": "operator@test.local",
    }


@pytest.mark.asyncio
async def test_journal_studio_settings_get_returns_snapshot(restore_overrides: None) -> None:
    from app.application.services.journal_studio_settings_service import JournalStudioSettingsOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    snapshot = JournalStudioSettingsOut(enabled=True, source="deployment")

    with patch(
        "app.presentation.api.routers.journal_studio.get_journal_studio_settings",
        AsyncMock(return_value=snapshot),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/settings",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["obsidian_subfolder"] == "Trading/Journal"


@pytest.mark.asyncio
async def test_journal_studio_settings_patch_persists(restore_overrides: None) -> None:
    from app.application.services.journal_studio_settings_service import JournalStudioSettingsOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    saved = JournalStudioSettingsOut(
        enabled=True,
        obsidian_subfolder="Vault/Trades",
        review_cron_preset="weekly_monday",
        review_cron="0 7 * * 1",
        source="tenant",
    )

    with (
        patch(
            "app.presentation.api.routers.journal_studio.save_journal_studio_settings",
            AsyncMock(return_value=saved),
        ),
        patch(
            "app.presentation.api.routers.journal_studio.ensure_journal_review_routine",
            AsyncMock(return_value={"status": "created"}),
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/journal-studio/settings",
                headers={"Authorization": "Bearer x"},
                json={"obsidian_subfolder": "Vault/Trades", "review_cron_preset": "weekly_monday"},
            )

    assert response.status_code == 200
    assert response.json()["obsidian_subfolder"] == "Vault/Trades"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_journal_studio_routine_bootstrap(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.presentation.api.routers.journal_studio.ensure_journal_review_routine",
        AsyncMock(return_value={"status": "created", "routine_id": str(uuid.uuid4())}),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/journal-studio/routine/bootstrap",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "created"
