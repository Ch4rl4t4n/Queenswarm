"""API unit tests for TJ3 journal gardener routes."""

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
        "sub": "operator@test.local",
    }


@pytest.mark.asyncio
async def test_journal_studio_gardener_get(restore_overrides: None) -> None:
    from app.application.services.journal_studio_gardener_service import JournalGardenerSnapshotOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    snapshot = JournalGardenerSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        pending_count=1,
    )

    with patch(
        "app.presentation.api.routers.journal_studio.compose_journal_gardener_snapshot",
        AsyncMock(return_value=snapshot),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/gardener",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["pending_count"] == 1


@pytest.mark.asyncio
async def test_journal_studio_gardener_draft_review(restore_overrides: None) -> None:
    from app.application.services.journal_studio_gardener_service import JournalDraftReviewOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    result = JournalDraftReviewOut(
        id="d1",
        status="published",
        wiki_slug="trading-journal-btc",
        reviewed_at=datetime.now(tz=UTC),
    )

    with patch(
        "app.presentation.api.routers.journal_studio.review_journal_draft",
        AsyncMock(return_value=result),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/journal-studio/gardener/drafts/d1/review",
                headers={"Authorization": "Bearer x"},
                json={"decision": "approve"},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    mock_db.commit.assert_awaited_once()
