"""Unit tests for Enterprise subscription Stripe checkout."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.application.services.enterprise_subscription_checkout import (
    CHECKOUT_KIND_ENTERPRISE,
    complete_enterprise_subscription_from_stripe,
    create_enterprise_checkout_session,
    enterprise_checkout_ready,
)
from app.core.config import settings


def test_enterprise_checkout_ready_when_price_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.enterprise_subscription_checkout.stripe_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(settings, "stripe_enterprise_price_id", "price_ent")
    assert enterprise_checkout_ready() is True


@pytest.mark.asyncio
async def test_create_enterprise_checkout_rejects_free_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = "11111111-1111-1111-1111-111111111111"
    subscription = SimpleNamespace(tier="free", stripe_customer_id=None)
    user = SimpleNamespace(id=tenant_id, email="ops@test.com")

    async def fake_ensure(_session: object, *, tenant_id: object) -> SimpleNamespace:
        return subscription

    monkeypatch.setattr(
        "app.application.services.enterprise_subscription_checkout.enterprise_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.application.services.enterprise_subscription_checkout.ensure_tenant_subscription",
        fake_ensure,
    )

    with pytest.raises(HTTPException) as exc:
        await create_enterprise_checkout_session(
            MagicMock(),
            tenant_id=tenant_id,  # type: ignore[arg-type]
            dashboard_user=user,  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_complete_enterprise_subscription_sets_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = "11111111-1111-1111-1111-111111111111"
    subscription = SimpleNamespace(
        tier="pro",
        status="active",
        stripe_customer_id=None,
        stripe_subscription_id=None,
        period_end_at=None,
        billing_cycle_anchor=None,
        updated_at=None,
    )
    checkout = SimpleNamespace(
        metadata={"queenswarm_checkout": CHECKOUT_KIND_ENTERPRISE, "tenant_id": tenant_id},
        customer="cus_ent",
        subscription="sub_ent",
    )
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.retrieve.return_value = checkout
    mock_stripe.Subscription.retrieve.return_value = SimpleNamespace(
        current_period_end=1_900_000_000,
        billing_cycle_anchor=1_800_000_000,
    )
    mock_session = MagicMock()
    mock_session.flush = AsyncMock()

    async def fake_ensure(_session: object, *, tenant_id: object) -> SimpleNamespace:
        return subscription

    monkeypatch.setattr(
        "app.application.services.enterprise_subscription_checkout.ensure_tenant_subscription",
        fake_ensure,
    )
    monkeypatch.setattr(
        "app.application.services.enterprise_subscription_checkout.stripe_effective_secret_key",
        lambda: "sk_test",
    )

    with patch.dict("sys.modules", {"stripe": mock_stripe}):
        upgraded = await complete_enterprise_subscription_from_stripe(
            mock_session,
            checkout_session_id="cs_ent",
        )

    assert upgraded is True
    assert subscription.tier == "enterprise"
