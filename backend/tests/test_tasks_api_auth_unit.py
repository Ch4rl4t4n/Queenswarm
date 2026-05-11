"""ASGI checks for task router authentication surface."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

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
async def test_tasks_list_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/tasks")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_tasks_list_returns_empty_with_mock_db(restore_app_overrides: None) -> None:
    token, _ = create_access_token(subject="pytest-operator", expires_minutes=5)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result)
        yield session

    app.dependency_overrides[require_subject] = lambda: "pytest-operator"
    app.dependency_overrides[get_db] = mock_db

    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/tasks", headers=headers)
    assert response.status_code == 200
    assert response.json() == []
