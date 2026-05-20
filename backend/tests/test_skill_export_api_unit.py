"""API routes for skill export and skills catalog."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.jwt_tokens import create_access_token
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role, require_subject
from app.infrastructure.persistence.models.recipe import Recipe


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_skills_catalog_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/recipes/skills-catalog")
    assert response.status_code in {401, 403}


@pytest.fixture
def tenant_auth_fixture(restore_app_overrides: None) -> uuid.UUID:
    """Inject dashboard tenant principal for skill marketplace routes."""

    tenant_id = uuid.uuid4()
    user = MagicMock()
    user.id = uuid.uuid4()
    user.is_active = True
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": user,
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": [],
    }
    return tenant_id


@pytest.mark.asyncio
async def test_export_skill_when_recipe_missing_returns_404(
    restore_app_overrides: None,
    tenant_auth_fixture: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del tenant_auth_fixture
    app.dependency_overrides[require_subject] = lambda: "pytest"
    monkeypatch.setattr(settings, "recipes_enabled", True)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}
    missing = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/recipes/{missing}/export-skill",
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_skill_when_recipe_present_returns_bundle(
    restore_app_overrides: None,
    tenant_auth_fixture: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del tenant_auth_fixture
    app.dependency_overrides[require_subject] = lambda: "pytest"
    monkeypatch.setattr(settings, "recipes_enabled", True)

    rid = uuid.uuid4()
    recipe = Recipe(
        id=rid,
        name="API Export",
        description="from test",
        topic_tags=["test"],
        workflow_template={"steps": [{"description": "run"}]},
        success_count=2,
        fail_count=0,
        avg_pollen_earned=5.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.get = AsyncMock(return_value=recipe)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/recipes/{rid}/export-skill",
            headers=headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["slug"] == "api-export"
    assert len(payload["files"]) == 6
    assert payload["files"][0]["path"].endswith("SKILL.md")


@pytest.mark.asyncio
async def test_skills_catalog_returns_builtin_and_recipes(
    restore_app_overrides: None,
    tenant_auth_fixture: uuid.UUID,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del tenant_auth_fixture
    app.dependency_overrides[require_subject] = lambda: "pytest"
    monkeypatch.setattr(settings, "recipes_enabled", True)

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
        response = await client.get("/api/v1/recipes/skills-catalog", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert "builtin" in body
    assert "recipes" in body
    assert any(row.get("slug") == "grill-me" for row in body["builtin"])
