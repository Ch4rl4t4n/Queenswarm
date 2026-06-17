"""Unit tests for FP4 commercial self-serve billing checkout."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.commercial_self_serve_service import (
    BillingCheckoutRequest,
    apply_commercial_checkout_session,
    compose_checkout_ready_flags,
    create_commercial_checkout_session,
    stripe_checkout_configured,
)


def test_stripe_checkout_configured_when_keys_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "commercial_self_serve_enabled", True)
    monkeypatch.setattr(settings, "stripe_secret_key", "")
    monkeypatch.setattr(settings, "stripe_pro_price_id", "price_test")
    assert stripe_checkout_configured(tier="pro") is False

    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test")
    assert stripe_checkout_configured(tier="pro") is True


def test_compose_checkout_ready_flags() -> None:
    flags = compose_checkout_ready_flags()
    assert "checkout_ready" in flags
    assert "pro_price_eur_cents" in flags


@pytest.mark.asyncio
async def test_apply_checkout_upgrades_tenant_tier() -> None:
    tenant_id = uuid.uuid4()
    subscription = SimpleNamespace(
        tier="free",
        status="active",
        billing_customer_id=None,
        billing_subscription_id=None,
        billing_cycle_anchor=None,
    )
    session = AsyncMock()
    session.flush = AsyncMock()

    with patch(
        "app.application.services.commercial_self_serve_service.ensure_tenant_subscription",
        AsyncMock(return_value=subscription),
    ):
        upgraded = await apply_commercial_checkout_session(
            session,
            checkout_object={
                "id": "cs_test",
                "payment_status": "paid",
                "customer": "cus_test",
                "subscription": "sub_test",
                "metadata": {
                    "queenswarm_purpose": "commercial_pro_upgrade",
                    "tenant_id": str(tenant_id),
                    "target_tier": "pro",
                },
            },
        )

    assert upgraded is True
    assert subscription.tier == "pro"
    assert subscription.billing_customer_id == "cus_test"
    assert subscription.billing_subscription_id == "sub_test"


@pytest.mark.asyncio
async def test_create_checkout_rejects_internal_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "commercial_self_serve_enabled", True)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test")
    monkeypatch.setattr(settings, "stripe_pro_price_id", "price_test")

    tenant = MagicMock(platform_mode="internal")
    session = AsyncMock()
    with pytest.raises(ValueError, match="commercial tenants"):
        await create_commercial_checkout_session(
            session,
            tenant_id=uuid.uuid4(),
            tenant=tenant,
            customer_email="ops@example.com",
            payload=BillingCheckoutRequest(),
        )


@pytest.mark.asyncio
async def test_create_checkout_calls_stripe(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "commercial_self_serve_enabled", True)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test")
    monkeypatch.setattr(settings, "stripe_pro_price_id", "price_test")
    monkeypatch.setattr(settings, "oauth_public_origin", "https://queenswarm.love")

    tenant_id = uuid.uuid4()
    tenant = MagicMock(platform_mode="commercial")
    subscription = SimpleNamespace(
        tier="free",
        billing_customer_id=None,
    )
    session = AsyncMock()

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"id": "cs_test", "url": "https://checkout.stripe.test/session"}

    class FakeClient:
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, *args: object, **kwargs: object) -> FakeResponse:
            return FakeResponse()

    with (
        patch(
            "app.application.services.commercial_self_serve_service.ensure_tenant_subscription",
            AsyncMock(return_value=subscription),
        ),
        patch("app.application.services.commercial_self_serve_service.httpx.AsyncClient", return_value=FakeClient()),
    ):
        out = await create_commercial_checkout_session(
            session,
            tenant_id=tenant_id,
            tenant=tenant,
            customer_email="ops@example.com",
            payload=BillingCheckoutRequest(),
        )

    assert out.checkout_url == "https://checkout.stripe.test/session"
    assert out.session_id == "cs_test"
