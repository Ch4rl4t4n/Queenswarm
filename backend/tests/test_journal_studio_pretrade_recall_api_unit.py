"""API unit tests for TJ5 pre-trade recall route."""

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
async def test_journal_studio_pretrade_recall_get(restore_overrides: None) -> None:
    from app.application.services.journal_studio_pretrade_recall_service import PreTradeRecallOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    recall = PreTradeRecallOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        mistake_count=1,
        operator_hint="1 mistake pattern",
    )

    with patch(
        "app.presentation.api.routers.journal_studio.compose_pretrade_recall",
        AsyncMock(return_value=recall),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/pretrade-recall",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["mistake_count"] == 1


@pytest.mark.asyncio
async def test_journal_studio_pretrade_recall_get_disabled(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    with patch(
        "app.presentation.api.routers.journal_studio.settings",
        type(
            "S",
            (),
            {"journal_studio_pretrade_recall_enabled": False, "journal_studio_enabled": True},
        )(),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/journal-studio/pretrade-recall",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 404
