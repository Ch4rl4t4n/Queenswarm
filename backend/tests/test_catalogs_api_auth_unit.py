"""JWT surface for simulations + recipes catalog."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db, require_subject
from app.core.jwt_tokens import create_access_token
from app.main import app
from app.schemas.recipes_search import RecipeSemanticHit


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_simulations_list_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulations")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_simulations_returns_rows_from_mock_session(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=exec_result)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulations", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_recipes_list_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recipes")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_recipes_list_empty_mock_db(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        exec_result = MagicMock()
        exec_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=exec_result)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recipes", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_recipes_search_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recipes/search", params={"q": "hello swarm"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_recipes_search_returns_hits_through_bridge(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db

    sample = RecipeSemanticHit(
        chroma_document_id="doc-1",
        similarity=0.91,
        distance=0.09,
        document_preview="probe",
        metadata={"source": "test"},
        postgres_recipe_id=None,
        postgres_row=None,
    )

    async def fake_search(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return [sample]

    monkeypatch.setattr(
        "app.api.routers.recipes.search_recipes_semantic",
        fake_search,
    )

    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/recipes/search",
            headers=headers,
            params={"q": "verify workflow", "limit": 3},
        )

    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["chroma_document_id"] == "doc-1"
    assert abs(rows[0]["similarity"] - 0.91) < 1e-6
