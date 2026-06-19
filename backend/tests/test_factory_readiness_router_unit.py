"""API unit tests for factory readiness export + LLM routes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.factory_export_readiness_service import FactoryExportReadinessOut
from app.application.services.factory_llm_readiness_service import FactoryLlmReadinessOut
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _owner_principal() -> dict[str, object]:
    tenant_id = uuid.uuid4()
    return {
        "user": type("U", (), {"id": uuid.uuid4()})(),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
        "sub": "auth0|test",
    }


@pytest.mark.asyncio
async def test_factory_export_readiness_get(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    payload = FactoryExportReadinessOut(
        manual_export_ready=True,
        github_pr_ready=True,
        github_setup_hint="ready",
    )

    with patch(
        "app.presentation.api.routers.factory_readiness.resolve_factory_export_readiness",
        AsyncMock(return_value=payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/factory-readiness/export",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["github_pr_ready"] is True


@pytest.mark.asyncio
async def test_factory_llm_readiness_get(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    payload = FactoryLlmReadinessOut(chain_usable=True, build_allowed=True, smoke_ok=True)

    with patch(
        "app.presentation.api.routers.factory_readiness.resolve_factory_llm_readiness",
        AsyncMock(return_value=payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/factory-readiness/llm",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["build_allowed"] is True


@pytest.mark.asyncio
async def test_factory_llm_set_primary_put(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = FactoryLlmReadinessOut(chain_usable=True, build_allowed=True, primary_model="openrouter/gpt-4o-mini")

    with patch(
        "app.presentation.api.routers.factory_readiness.save_factory_llm_primary",
        AsyncMock(),
    ):
        with patch(
            "app.presentation.api.routers.factory_readiness.resolve_factory_llm_readiness",
            AsyncMock(return_value=payload),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    "/api/v1/factory-readiness/llm/primary",
                    headers={"Authorization": "Bearer x"},
                    json={"primary_model": "openrouter/gpt-4o-mini"},
                )

    assert response.status_code == 200
    assert response.json()["primary_model"] == "openrouter/gpt-4o-mini"


@pytest.mark.asyncio
async def test_factory_llm_smoke_post(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    payload = FactoryLlmReadinessOut(chain_usable=True, build_allowed=True, smoke_ok=True)

    with patch(
        "app.presentation.api.routers.factory_readiness.run_factory_llm_smoke",
        AsyncMock(return_value=payload),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/factory-readiness/llm/smoke",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["smoke_ok"] is True
