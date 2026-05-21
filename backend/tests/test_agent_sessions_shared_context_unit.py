"""ASGI tests for supervisor shared-context preview endpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.supervisor.shared_context import RetrievalBundle, SharedContextService
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import agent_sessions as sessions_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset DI overrides between tests."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_shared_context_endpoint_when_disabled_returns_enabled_false(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preview endpoint returns summary without resolving bundle when flag is off."""

    session_id = uuid.uuid4()
    session = SimpleNamespace(
        id=session_id,
        goal="Research competitor pricing",
        context_summary={"retrieval_contract": "policy+semantic_memory", "raw_goal": "Research competitor pricing"},
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "sub": "dash:operator",
        "tenant_role": "owner",
    }
    monkeypatch.setattr(sessions_router, "get_supervisor_session", _fake_get_session)
    monkeypatch.setattr(sessions_router.settings, "retrieval_contract_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/shared-context")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["retrieval_contract"] == "policy+semantic_memory"


@pytest.mark.asyncio
async def test_shared_context_endpoint_when_enabled_returns_bundle(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preview endpoint resolves retrieval bundle when feature flag is on."""

    session_id = uuid.uuid4()
    session = SimpleNamespace(
        id=session_id,
        goal="Ship onboarding flow",
        context_summary={"retrieval_contract": "policy", "raw_goal": "Ship onboarding flow"},
    )
    bundle = RetrievalBundle(
        contract="policy",
        sections={"policy": [{"document": "Always verify before user-facing output."}]},
        matched_sections=["policy"],
        relevance_scores={"policy": 0.91},
        pruned_items=1,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_get_session(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return session

    async def _fake_retrieve(self, db, *, supervisor_session_id, query, contract):  # noqa: ANN001, ANN202
        del self, db, supervisor_session_id, query, contract
        return bundle

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "sub": "dash:operator",
        "tenant_role": "owner",
    }
    monkeypatch.setattr(sessions_router, "get_supervisor_session", _fake_get_session)
    monkeypatch.setattr(sessions_router.settings, "retrieval_contract_enabled", True)
    monkeypatch.setattr(SharedContextService, "retrieve_context_bundle", _fake_retrieve)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/agents/sessions/{session_id}/shared-context")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["matched_sections"] == ["policy"]
    assert body["pruned_items"] == 1
    assert "policy" in body["prompt_block"]
