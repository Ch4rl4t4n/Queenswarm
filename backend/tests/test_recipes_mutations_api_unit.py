"""JWT + mutation paths for Recipe Library HTTP surface."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db, require_subject
from app.core.jwt_tokens import create_access_token
from app.main import app


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_recipe_requires_bearer(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            json={
                "name": "x",
                "workflow_template": {"steps": []},
            },
        )
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_create_recipe_returns_201_when_service_succeeds(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="hive-recipe",
        description=None,
        topic_tags=[],
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )

    async def fake_create(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr("app.api.routers.recipes.create_recipe_entry", fake_create)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={
                "name": "hive-recipe",
                "workflow_template": {"steps": [{"description": "probe"}]},
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "hive-recipe"


@pytest.mark.asyncio
async def test_get_recipe_returns_404_when_missing(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}
    rid = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/recipes/{rid}", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_recipe_empty_body_returns_400(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}
    rid = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(f"/api/v1/recipes/{rid}", headers=headers, json={})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_recipe_returns_row(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"
    rid = uuid.uuid4()
    row = SimpleNamespace(
        id=rid,
        name="n",
        description=None,
        topic_tags=[],
        success_count=1,
        fail_count=0,
        avg_pollen_earned=1.5,
        embedding_id="emb",
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.get = AsyncMock(return_value=row)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/recipes/{rid}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(rid)


@pytest.mark.asyncio
async def test_patch_recipe_returns_200_when_update_succeeds(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app.dependency_overrides[require_subject] = lambda: "pytest"
    rid = uuid.uuid4()

    stub = SimpleNamespace(
        id=rid,
        name="renamed",
        description="d",
        topic_tags=["t"],
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=True,
    )

    async def fake_update(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr("app.api.routers.recipes.update_recipe_entry", fake_update)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/recipes/{rid}",
            headers=headers,
            json={"name": "renamed", "is_deprecated": True},
        )

    assert response.status_code == 200
    assert response.json()["name"] == "renamed"
    assert response.json()["is_deprecated"] is True


@pytest.mark.asyncio
async def test_create_recipe_forbidden_when_mutations_disabled(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.config as core_config

    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutations_enabled", False)

    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={"name": "blocked", "workflow_template": {"steps": []}},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_recipe_forbidden_when_not_in_allowlist(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.config as core_config

    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutations_enabled", True)
    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutation_allowlist", ["keeper"])

    token, _ = create_access_token(subject="guest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={"name": "x", "workflow_template": {"steps": []}},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_recipe_allows_allowlisted_subject(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.config as core_config

    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutations_enabled", True)
    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutation_allowlist", ["keeper"])

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="allow",
        description=None,
        topic_tags=[],
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )

    async def fake_create(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr("app.api.routers.recipes.create_recipe_entry", fake_create)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="keeper")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={"name": "allow", "workflow_template": {"steps": []}},
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_recipe_forbidden_when_required_scope_missing(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.config as core_config

    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutations_enabled", True)
    monkeypatch.setattr(
        core_config.settings,
        "recipe_catalog_mutation_required_scope",
        "recipes:write",
    )

    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={"name": "scope-miss", "workflow_template": {"steps": []}},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_recipe_ok_when_required_scope_present(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.config as core_config

    monkeypatch.setattr(core_config.settings, "recipe_catalog_mutations_enabled", True)
    monkeypatch.setattr(
        core_config.settings,
        "recipe_catalog_mutation_required_scope",
        "recipes:write",
    )

    stub = SimpleNamespace(
        id=uuid.uuid4(),
        name="scoped",
        description=None,
        topic_tags=[],
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )

    async def fake_create(*args, **kwargs):  # noqa: ANN002,ANN003
        del args, kwargs
        return stub

    monkeypatch.setattr("app.api.routers.recipes.create_recipe_entry", fake_create)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest", scope="recipes:write")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={"name": "scoped", "workflow_template": {"steps": []}},
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_recipe_413_when_workflow_template_too_large(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.core.config as core_config

    monkeypatch.setattr(core_config.settings, "recipe_workflow_template_max_json_bytes", 1024)

    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.execute = AsyncMock(return_value=exec_result)
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/recipes",
            headers=headers,
            json={
                "name": "oversize-rw-test",
                "workflow_template": {"blob": "x" * 3000},
            },
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_delete_recipe_requires_bearer(restore_app_overrides: None) -> None:
    rid = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/recipes/{rid}")
    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_delete_recipe_returns_204_when_service_succeeds(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rid = uuid.uuid4()

    async def fake_delete(*args, **kwargs):  # noqa: ANN002,ANN003
        return rid, "gone"

    monkeypatch.setattr("app.api.routers.recipes.delete_recipe_entry", fake_delete)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.commit = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/recipes/{rid}", headers=headers)

    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.asyncio
async def test_delete_recipe_returns_404_when_missing(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.recipe_write import RecipeWriteNotFoundError

    async def fake_delete(*args, **kwargs):  # noqa: ANN002,ANN003
        raise RecipeWriteNotFoundError

    monkeypatch.setattr("app.api.routers.recipes.delete_recipe_entry", fake_delete)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.rollback = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    rid = uuid.uuid4()
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/recipes/{rid}", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_recipe_returns_409_when_referenced(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.recipe_write import RecipeWriteReferencedError

    async def fake_delete(*args, **kwargs):  # noqa: ANN002,ANN003
        raise RecipeWriteReferencedError(reference_count=3)

    monkeypatch.setattr("app.api.routers.recipes.delete_recipe_entry", fake_delete)

    async def mock_db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.rollback = AsyncMock()
        yield session

    app.dependency_overrides[get_db] = mock_db
    rid = uuid.uuid4()
    token, _ = create_access_token(subject="pytest")
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/recipes/{rid}", headers=headers)

    assert response.status_code == 409
    assert "3 dependent" in response.json()["detail"]
