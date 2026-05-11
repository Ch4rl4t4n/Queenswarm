"""Deferred swarm runs enqueue Celery with ledger + deterministic task id."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db, require_subject
from app.core.jwt_tokens import create_access_token
from app.main import app


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_defer_run_returns_202_with_task_id(restore_app_overrides: None) -> None:
    swarm = "11111111-1111-1111-1111-111111111111"
    workflow = "22222222-2222-2222-2222-222222222222"

    async def mock_db() -> AsyncIterator[MagicMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    captured: dict[str, object] = {}

    def fake_apply_async(*_a: object, **kw: object) -> MagicMock:
        captured.update(kw)
        return MagicMock()

    with (
        patch("app.api.routers.swarms.enqueue_hive_async_workflow_run", new_callable=AsyncMock),
        patch(
            "app.worker.tasks.run_sub_swarm_workflow_cycle_task.apply_async",
            side_effect=fake_apply_async,
        ) as mocked_apply,
    ):
        app.dependency_overrides[require_subject] = lambda: "pytest"
        app.dependency_overrides[get_db] = mock_db

        transport = ASGITransport(app=app)
        token, _ = create_access_token(subject="pytest")
        headers = {"Authorization": f"Bearer {token}"}
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/swarms/{swarm}/workflows/{workflow}/run",
                json={"defer_to_worker": True},
                headers=headers,
            )

    assert response.status_code == 202
    mocked_apply.assert_called_once()
    data = response.json()
    assert len(data["celery_task_id"]) == 36
    assert data["celery_task_id"] == captured.get("task_id")
    kw_payload = captured.get("kwargs") or {}
    assert kw_payload["ledger_tracking_id"] == data["celery_task_id"]
    assert data["status"] == "queued"
    assert data["swarm_id"] == swarm
    assert data["workflow_id"] == workflow
