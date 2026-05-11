"""ASGI tests for Phase F catalog routers (agents, swarm CRUD, simulation writes)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.core.jwt_tokens import create_access_token
from app.main import app
from app.models.enums import AgentRole, AgentStatus, SimulationResult, SwarmPurpose


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
async def test_create_agent_returns_201_when_service_succeeds(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routers import agents as agents_router

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="bee-x",
        role=AgentRole.LEARNER,
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

    async def fake_create(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(agents_router, "create_agent_record", fake_create)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

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

    assert r.status_code == 201
    assert r.json()["name"] == "bee-x"


@pytest.mark.asyncio
async def test_list_sub_swarms_returns_rows(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import swarms as swarms_router

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="c1",
        purpose=SwarmPurpose.SCOUT,
        local_memory={},
        queen_agent_id=None,
        last_global_sync_at=None,
        total_pollen=0.0,
        member_count=0,
        is_active=True,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_list(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return [stub]

    monkeypatch.setattr(swarms_router, "list_sub_swarms", fake_list)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/swarms", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "c1"


@pytest.mark.asyncio
async def test_create_simulation_returns_422_when_task_missing(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routers import simulations as sim_router
    from app.services.simulation_audit import SimulationAuditError

    async def boom(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        raise SimulationAuditError("bad task")

    monkeypatch.setattr(sim_router, "create_simulation_record", boom)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/simulations",
            headers=headers,
            json={
                "task_id": str(uuid.uuid4()),
                "scenario": {},
                "result_type": "pass",
                "confidence_pct": 90.0,
            },
        )

    assert r.status_code == 422


@pytest.mark.asyncio
async def test_get_simulation_returns_404_when_missing(restore_app_overrides: None) -> None:
    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}
    sid = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(f"/api/v1/simulations/{sid}", headers=headers)

    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_sub_swarm_returns_201(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import swarms as swarms_router

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="new-colony",
        purpose=SwarmPurpose.EVAL,
        local_memory={},
        queen_agent_id=None,
        last_global_sync_at=None,
        total_pollen=0.0,
        member_count=0,
        is_active=True,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_create(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(swarms_router, "create_sub_swarm", fake_create)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/swarms",
            headers=headers,
            json={
                "name": "new-colony",
                "purpose": "eval",
                "local_memory": {},
            },
        )

    assert r.status_code == 201
    assert r.json()["name"] == "new-colony"


@pytest.mark.asyncio
async def test_list_agents_returns_rows(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import agents as agents_router

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

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

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
async def test_create_simulation_returns_201_when_ok(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.routers import simulations as sim_router

    sim_id = uuid.uuid4()
    stub = SimpleNamespace(
        id=sim_id,
        task_id=None,
        scenario={"k": 1},
        result_type=SimulationResult.PASS,
        confidence_pct=92.0,
        result_data={"ok": True},
        docker_container_id="c1",
        duration_sec=0.1,
        stdout="out",
        stderr=None,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_create(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(sim_router, "create_simulation_record", fake_create)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/simulations",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "scenario": {"probe": True},
                "result_type": "pass",
                "confidence_pct": 92.0,
            },
        )

    assert r.status_code == 201
    assert r.json()["id"] == str(sim_id)


@pytest.mark.asyncio
async def test_get_agent_returns_200(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import agents as agents_router

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

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

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
async def test_patch_sub_swarm_returns_200(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import swarms as swarms_router

    sid = uuid.uuid4()
    stub = SimpleNamespace(
        id=sid,
        name="patched",
        purpose=SwarmPurpose.ACTION,
        local_memory={"x": 2},
        queen_agent_id=None,
        last_global_sync_at=None,
        total_pollen=1.0,
        member_count=2,
        is_active=True,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_fetch(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    async def fake_apply(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(swarms_router, "fetch_sub_swarm", fake_fetch)
    monkeypatch.setattr(swarms_router, "apply_sub_swarm_updates", fake_apply)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.patch(
            f"/api/v1/swarms/{sid}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "patched"},
        )

    assert r.status_code == 200
    assert r.json()["name"] == "patched"


@pytest.mark.asyncio
async def test_get_sub_swarm_returns_200(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import swarms as swarms_router

    sid = uuid.uuid4()
    stub = SimpleNamespace(
        id=sid,
        name="colony-get",
        purpose=SwarmPurpose.SCOUT,
        local_memory={},
        queen_agent_id=None,
        last_global_sync_at=None,
        total_pollen=0.0,
        member_count=1,
        is_active=True,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_fetch(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(swarms_router, "fetch_sub_swarm", fake_fetch)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            f"/api/v1/swarms/{sid}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert r.json()["id"] == str(sid)


@pytest.mark.asyncio
async def test_patch_agent_returns_200(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import agents as agents_router

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

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
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
async def test_list_simulations_returns_rows(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import simulations as sim_router

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        task_id=None,
        result_type=SimulationResult.PASS,
        confidence_pct=80.0,
        scenario={},
        docker_container_id=None,
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_list(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return [stub]

    monkeypatch.setattr(sim_router, "list_recent_simulation_audits", fake_list)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            "/api/v1/simulations",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_get_simulation_returns_detail(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routers import simulations as sim_router

    sid = uuid.uuid4()
    stub = SimpleNamespace(
        id=sid,
        task_id=None,
        result_type=SimulationResult.PASS,
        confidence_pct=99.0,
        scenario={"s": 1},
        result_data={"r": 2},
        docker_container_id="dx",
        duration_sec=2.0,
        stdout="a",
        stderr="b",
        created_at=_dt(),
        updated_at=_dt(),
    )

    async def fake_fetch(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr(sim_router, "fetch_simulation_audit", fake_fetch)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(
            f"/api/v1/simulations/{sid}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    assert r.json()["confidence_pct"] == 99.0
