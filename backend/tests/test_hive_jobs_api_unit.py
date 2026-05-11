"""Poll hive Celery AsyncResult façade."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db, require_subject
from app.core.jwt_tokens import create_access_token
from app.main import app
from app.worker.celery_app import celery_app


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


async def mock_ledger_lookup_db() -> AsyncIterator[AsyncMock]:
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=exec_result)
    yield session


@pytest.mark.asyncio
async def test_get_job_requires_auth(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/jobs/any-id")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_job_returns_success_blob(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"
    app.dependency_overrides[get_db] = mock_ledger_lookup_db
    mock_ar = MagicMock()
    mock_ar.state = "SUCCESS"
    mock_ar.ready.return_value = True
    mock_ar.successful.return_value = True
    mock_ar.result = {"ok": True, "swarm_id": "11111111-1111-1111-1111-111111111111"}

    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(celery_app, "AsyncResult", return_value=mock_ar):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/jobs/task-uuid-1", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "SUCCESS"
    assert data["ready"] is True
    assert data["successful"] is True
    assert data["workflow_result"]["ok"] is True
    assert data["postgres_ledger"] is None


@pytest.mark.asyncio
async def test_get_job_failure_surfaces_error(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"
    app.dependency_overrides[get_db] = mock_ledger_lookup_db
    mock_ar = MagicMock()
    mock_ar.state = "FAILURE"
    mock_ar.ready.return_value = True
    mock_ar.successful.return_value = False
    mock_ar.result = RuntimeError("worker blew up")

    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    with patch.object(celery_app, "AsyncResult", return_value=mock_ar):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/jobs/task-uuid-2", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["successful"] is False
    assert body["workflow_result"] is None
    assert "RuntimeError" in (body["error"] or "")
    assert body["postgres_ledger"] is None
