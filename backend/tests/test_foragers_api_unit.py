"""ASGI tests for /api/v1/foragers routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import foragers as foragers_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset dependency overrides across test cases."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:test"},
        "sub": "dash:test",
    }
    yield
    app.dependency_overrides.clear()


def _mk_forager() -> SimpleNamespace:
    now = datetime.now(tz=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        name="Macro Scout",
        description="🐝 Track macro changes",
        source_type="rss",
        source_config={"feeds": ["https://example.com/feed.xml"]},
        filter_config={"default_tags": ["macro"]},
        prompt_template="Summarize the delta.",
        tools=["rss", "web_search"],
        is_active=True,
        agent_template_id=None,
        supervisor_routine_id=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_foragers_list_returns_rows(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """List endpoint should return serialized tenant rows."""

    fake = _mk_forager()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(commit=lambda: None)

    async def _fake_list(self, tenant_id):  # noqa: ANN001
        del self, tenant_id
        return [fake]

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(foragers_router.ForagerService, "list_by_tenant", _fake_list)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/foragers", headers={"Authorization": "Bearer x"})

    assert res.status_code == 200
    payload = res.json()
    assert isinstance(payload, list)
    assert payload[0]["id"] == str(fake.id)
    assert payload[0]["name"] == "Macro Scout"


@pytest.mark.asyncio
async def test_foragers_create_returns_201(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create endpoint should return created entity payload."""

    fake = _mk_forager()

    async def _commit() -> None:
        return None

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(commit=_commit)

    async def _fake_create(self, **kwargs):  # noqa: ANN003
        del self, kwargs
        return fake

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(foragers_router.ForagerService, "create", _fake_create)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/foragers",
            headers={"Authorization": "Bearer x"},
            json={
                "name": "Macro Scout",
                "description": "Track macro shifts",
                "source_type": "rss",
                "source_config": {"feeds": ["https://example.com/feed.xml"]},
                "filter_config": {"default_tags": ["macro"]},
                "prompt_template": "Summarize.",
                "tools": ["rss"],
                "is_active": True,
                "schedule": {"enabled": False},
            },
        )

    assert res.status_code == 201
    body = res.json()
    assert body["id"] == str(fake.id)
    assert body["source_type"] == "rss"


@pytest.mark.asyncio
async def test_foragers_trigger_returns_summary(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Trigger endpoint should return manual-run summary envelope."""

    forager_id = uuid.uuid4()

    async def _commit() -> None:
        return None

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(commit=_commit)

    async def _fake_trigger(self, **kwargs):  # noqa: ANN003
        del self, kwargs
        return {
            "forager_id": str(forager_id),
            "ingested": 1,
            "routine_triggered": True,
            "routine_session_id": str(uuid.uuid4()),
            "status": "triggered",
        }

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(foragers_router.ForagerService, "trigger_manual_run", _fake_trigger)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/foragers/{forager_id}/trigger",
            headers={"Authorization": "Bearer x"},
            json={"records": [{"content_text": "Signal A", "topic_tags": ["macro"]}]},
        )

    assert res.status_code == 200
    payload = res.json()
    assert payload["forager_id"] == str(forager_id)
    assert payload["status"] == "triggered"
    assert payload["ingested"] == 1
