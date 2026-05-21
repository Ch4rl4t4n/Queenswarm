"""API coverage for tracer bullet slice-to-kanban route."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_subject
from app.presentation.api.routers import workflows as workflows_router


@pytest.fixture
def workflow_auth_fixture() -> Generator[None, None, None]:
    """JWT subject + DB session for workflow routes."""

    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()

    async def _db() -> AsyncIterator[AsyncMock]:
        yield mock_db

    app.dependency_overrides[require_subject] = lambda: f"dash:{uuid.uuid4()}"
    app.dependency_overrides[get_db] = _db
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_slice_to_kanban_route_returns_slices(
    monkeypatch: pytest.MonkeyPatch,
    workflow_auth_fixture: None,
) -> None:
    """POST slice-to-kanban returns parent + slice count."""

    workflow_id = uuid.uuid4()
    parent_id = uuid.uuid4()
    slice_id = uuid.uuid4()
    now = "2026-05-21T08:00:00+00:00"

    async def _fake_slice(*_args: object, **_kwargs: object) -> MagicMock:
        result = MagicMock()
        result.workflow_id = workflow_id
        result.parent_task_id = parent_id
        result.slice_count = 1
        result.idempotent_reuse = False
        return result

    async def _fake_response(_session: object, _result: object) -> dict[str, object]:
        return {
            "workflow_id": str(workflow_id),
            "parent_task_id": str(parent_id),
            "slice_count": 1,
            "idempotent_reuse": False,
            "parent": {
                "id": str(parent_id),
                "title": "Parent",
                "status": "pending",
                "task_type": "agent_run",
                "priority": 5,
                "payload": {},
                "result": None,
                "agent_id": None,
                "swarm_id": None,
                "workflow_id": str(workflow_id),
                "parent_task_id": None,
                "pollen_awarded": 0.0,
                "error_msg": None,
                "created_at": now,
                "updated_at": now,
                "completed_at": None,
                "agent_name": None,
            },
            "slices": [
                {
                    "id": str(slice_id),
                    "title": "Slice 1: scrape",
                    "status": "pending",
                    "task_type": "scrape",
                    "priority": 5,
                    "payload": {},
                    "result": None,
                    "agent_id": None,
                    "swarm_id": None,
                    "workflow_id": str(workflow_id),
                    "parent_task_id": str(parent_id),
                    "pollen_awarded": 0.0,
                    "error_msg": None,
                    "created_at": now,
                    "updated_at": now,
                    "completed_at": None,
                    "agent_name": None,
                },
            ],
        }

    monkeypatch.setattr(workflows_router, "slice_workflow_to_kanban", _fake_slice)
    monkeypatch.setattr(workflows_router, "build_slice_to_kanban_response", _fake_response)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/api/v1/workflows/{workflow_id}/slice-to-kanban",
            json={"priority": 5},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["slice_count"] == 1
    assert body["idempotent_reuse"] is False
