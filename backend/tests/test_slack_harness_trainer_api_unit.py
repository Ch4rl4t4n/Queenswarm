"""API coverage for Slack harness trainer feedback route."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.slack_harness_trainer import SlackTrainerResult
from app.domain.memory.curated import CuratedFileKind
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role, require_subject
from app.presentation.api.routers import harness as harness_router


@pytest.fixture
def slack_trainer_auth_fixture() -> Generator[None, None, None]:
    """Owner principal with mocked DB session."""

    tenant_id = uuid.uuid4()
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "owner@queenswarm.love"
    user.display_name = "Owner"

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    async def _db() -> AsyncIterator[AsyncMock]:
        yield mock_db

    app.dependency_overrides[require_subject] = lambda: f"dash:{user.id}"
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": [],
        "user": user,
    }
    app.dependency_overrides[get_db] = _db
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_slack_trainer_feedback_route(
    monkeypatch: pytest.MonkeyPatch,
    slack_trainer_auth_fixture: None,
) -> None:
    """Dashboard feedback append returns version metadata."""

    tenant_id = uuid.uuid4()

    async def _fake_append(*_args: object, **_kwargs: object) -> SlackTrainerResult:
        return SlackTrainerResult(
            tenant_id=tenant_id,
            kind=CuratedFileKind.INSTRUCTIONS,
            version=3,
            char_count=512,
            appended_chars=88,
            source="dashboard",
            author="owner@queenswarm.love",
        )

    async def _fake_notify(**_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(harness_router, "append_behavioral_feedback", _fake_append)
    monkeypatch.setattr(harness_router, "notify_trainer_confirmation", _fake_notify)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/harness/slack-trainer/feedback",
            json={"feedback": "Always verify simulations before user-facing reports.", "source": "dashboard"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == 3
    assert body["char_count"] == 512
    assert body["slack_notified"] is True
