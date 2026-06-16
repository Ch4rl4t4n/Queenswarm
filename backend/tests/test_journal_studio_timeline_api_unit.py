"""API unit tests for TJ1 journal studio timeline routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
    }


@pytest.mark.asyncio
async def test_journal_studio_timeline_get(restore_overrides: None) -> None:
    from app.application.services.journal_studio_timeline_service import JournalTimelineOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    timeline = JournalTimelineOut(enabled=True, generated_at=datetime.now(tz=UTC), entry_count=2)

    with patch(
        "app.presentation.api.routers.journal_studio.compose_journal_timeline",
        AsyncMock(return_value=timeline),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/timeline",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["entry_count"] == 2


@pytest.mark.asyncio
async def test_journal_studio_snapshot_get(restore_overrides: None) -> None:
    from app.application.services.journal_studio_timeline_service import JournalStudioWorkspaceSnapshotOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    snapshot = JournalStudioWorkspaceSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        enabled_field_count=5,
    )

    with patch(
        "app.presentation.api.routers.journal_studio.compose_journal_studio_workspace_snapshot",
        AsyncMock(return_value=snapshot),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/snapshot",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["enabled_field_count"] == 5
