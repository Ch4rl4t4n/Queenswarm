"""ASGI tests for trimmed catalog routers (agents + dashboard)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.presentation.api.deps import get_db
from app.core.jwt_tokens import create_access_token
from app.main import app
from app.models.enums import AgentRole, AgentStatus


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _dt() -> datetime:
    return datetime.now(tz=UTC)


@pytest.mark.asyncio
async def test_list_agents_requires_auth(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/agents")
    assert r.status_code in {401, 403}


@pytest.mark.asyncio
async def test_register_agent_returns_410(restore_app_overrides: None) -> None:
    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/agents",
            headers=headers,
            json={
                "name": "bee-x",
                "role": "learner",
                "config": {},
            },
        )

    assert r.status_code == 410


@pytest.mark.asyncio
async def test_list_agents_returns_rows(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.presentation.api.routers import agents as agents_router

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="bee-z",
        role=AgentRole.REPORTER,
        status=AgentStatus.RUNNING,
        swarm_id=None,
        config={},
        pollen_points=1.0,
        performance_score=0.3,
        last_synced_at=None,
        last_active_at=None,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_list(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return [stub]

    monkeypatch.setattr(agents_router, "list_agents", fake_list)
    monkeypatch.setattr(agents_router, "latest_open_tasks_for_agents", AsyncMock(return_value={}))

    scalar_bundle = MagicMock()
    scalar_bundle.all.return_value = []

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.scalars = AsyncMock(return_value=scalar_bundle)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert r.json()[0]["name"] == "bee-z"


@pytest.mark.asyncio
async def test_get_agent_returns_200(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.presentation.api.routers import agents as agents_router

    aid = uuid.uuid4()
    stub = SimpleNamespace(
        id=aid,
        name="bee-get",
        role=AgentRole.SCRAPER,
        status=AgentStatus.IDLE,
        swarm_id=None,
        config={},
        pollen_points=0.0,
        performance_score=0.0,
        last_synced_at=None,
        last_active_at=None,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_fetch(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(agents_router, "fetch_agent", fake_fetch)
    monkeypatch.setattr(agents_router, "latest_open_tasks_for_agents", AsyncMock(return_value={}))

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            f"/api/v1/agents/{aid}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert r.json()["id"] == str(aid)


@pytest.mark.asyncio
async def test_patch_agent_returns_200(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.presentation.api.routers import agents as agents_router

    aid = uuid.uuid4()
    stub = SimpleNamespace(
        id=aid,
        name="bee-patch",
        role=AgentRole.SIMULATOR,
        status=AgentStatus.IDLE,
        swarm_id=None,
        config={},
        pollen_points=2.0,
        performance_score=0.4,
        last_synced_at=None,
        last_active_at=None,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_fetch(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    async def fake_apply(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(agents_router, "fetch_agent", fake_fetch)
    monkeypatch.setattr(agents_router, "apply_agent_updates", fake_apply)

    monkeypatch.setattr(agents_router, "latest_open_tasks_for_agents", AsyncMock(return_value={}))

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.scalar = AsyncMock(return_value=None)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.patch(
            f"/api/v1/agents/{aid}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "running"},
        )

    assert r.status_code == 200
    assert r.json()["name"] == "bee-patch"


@pytest.mark.asyncio
async def test_dashboard_summary_requires_auth(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/dashboard/summary")
    assert r.status_code in {401, 403}
