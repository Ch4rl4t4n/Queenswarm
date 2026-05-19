"""ASGI tests for /api/v1/billing/stripe-config settings vault."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset dependency overrides across test cases."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4(), is_admin=True, is_active=True),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:00000000-0000-4000-8000-000000000001"},
        "sub": "dash:00000000-0000-4000-8000-000000000001",
    }
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stripe_config_get_when_unconfigured_returns_masked_none(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings panel should expose checkout readiness without plaintext secrets."""

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(commit=lambda: None, get=lambda *_a, **_k: None)

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(
        "app.presentation.api.routers.billing.stripe_effective_secret_key",
        lambda: "",
    )
    monkeypatch.setattr(
        "app.presentation.api.routers.billing.stripe_effective_webhook_secret",
        lambda: "",
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/billing/stripe-config", headers={"Authorization": "Bearer x"})

    assert res.status_code == 200
    payload = res.json()
    assert payload["checkout_ready"] is False
    assert payload["secret_key_masked"] is None
    assert payload["webhook_url"].endswith("/api/v1/billing/stripe/webhook")


@pytest.mark.asyncio
async def test_stripe_config_put_when_admin_principal_uses_user_object(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PUT must read admin from principal.user (not top-level sub)."""

    admin = SimpleNamespace(id=uuid.uuid4(), is_admin=True, is_active=True)
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": admin,
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": f"dash:{admin.id}"},
    }

    persisted: dict[str, object] = {}

    async def _fake_persist(session, **kwargs):  # noqa: ANN001, ARG001
        persisted.update(kwargs)

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        db = SimpleNamespace(commit=_commit, rollback=lambda: None)
        yield db

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(
        "app.presentation.api.routers.billing.persist_stripe_secrets",
        _fake_persist,
    )
    monkeypatch.setattr(
        "app.presentation.api.routers.billing.stripe_effective_secret_key",
        lambda: "sk_test_" + "a" * 24,
    )
    monkeypatch.setattr(
        "app.presentation.api.routers.billing.stripe_effective_webhook_secret",
        lambda: "whsec_" + "b" * 24,
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.put(
            "/api/v1/billing/stripe-config",
            headers={"Authorization": "Bearer x"},
            json={"secret_key": "sk_test_" + "c" * 24, "webhook_secret": "whsec_" + "d" * 24},
        )

    assert res.status_code == 200
    assert persisted.get("secret_key", "").startswith("sk_test_")
    assert res.json()["checkout_ready"] is True
