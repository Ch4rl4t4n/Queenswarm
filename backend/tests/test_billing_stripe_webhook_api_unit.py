"""ASGI tests for Stripe billing webhook (no JWT — signature verified instead)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.presentation.api.deps import get_db


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset dependency overrides across test cases."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stripe_webhook_when_secret_missing_returns_503_not_401(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Webhook must stay public; missing config yields 503, never JWT 401."""

    monkeypatch.setattr(settings, "stripe_webhook_secret", "")
    monkeypatch.setattr(settings, "stripe_secret_key", "")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/billing/stripe/webhook", content=b"{}")
    assert res.status_code == 503
    assert res.status_code != 401


@pytest.mark.asyncio
async def test_stripe_webhook_when_secret_set_missing_signature_returns_400(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured webhook rejects unsigned payloads before Stripe verification."""

    async def mock_db() -> AsyncIterator[object]:
        yield object()

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret")
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_placeholder")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/billing/stripe/webhook", content=b"{}")
    assert res.status_code == 400
    assert res.json()["detail"] == "Missing stripe-signature header."
