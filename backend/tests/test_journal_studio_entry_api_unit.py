"""API unit tests for TJ2 journal trade entry routes."""

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
    }


@pytest.mark.asyncio
async def test_journal_studio_entries_get(restore_overrides: None) -> None:
    from app.application.services.journal_studio_entry_service import JournalTradeEntryListOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = JournalTradeEntryListOut(entry_count=1, enabled_fields=["thesis", "lesson"])

    with patch(
        "app.presentation.api.routers.journal_studio.list_journal_trade_entries",
        AsyncMock(return_value=payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/entries",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["entry_count"] == 1


@pytest.mark.asyncio
async def test_journal_studio_entries_post(restore_overrides: None) -> None:
    from app.application.services.journal_studio_entry_service import JournalTradeEntryOut
    from datetime import UTC, datetime

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    now = datetime.now(tz=UTC)
    entry = JournalTradeEntryOut(id=str(uuid.uuid4()), occurred_at=now, created_at=now, updated_at=now)

    with patch(
        "app.presentation.api.routers.journal_studio.create_journal_trade_entry",
        AsyncMock(return_value=entry),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/journal-studio/entries",
                headers={"Authorization": "Bearer x"},
                json={"thesis": "Test thesis", "lesson": "Test lesson"},
            )

    assert response.status_code == 200
    mock_db.commit.assert_awaited_once()
