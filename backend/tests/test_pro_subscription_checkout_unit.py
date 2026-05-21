"""Unit tests for Pro subscription Stripe checkout."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.pro_subscription_checkout import (
    CHECKOUT_KIND_PRO,
    complete_pro_subscription_from_stripe,
    pro_checkout_ready,
)
from app.core.config import settings


def test_pro_checkout_ready_when_secret_and_price_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pro checkout requires Stripe secret and price configuration."""

    monkeypatch.setattr(
        "app.application.services.pro_subscription_checkout.stripe_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(settings, "stripe_pro_price_id", "price_test_pro")
    assert pro_checkout_ready() is True


def test_pro_checkout_ready_when_secret_and_fallback_cents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dynamic price_data fallback works when price id is unset."""

    monkeypatch.setattr(
        "app.application.services.pro_subscription_checkout.stripe_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(settings, "stripe_pro_price_id", "")
    monkeypatch.setattr(settings, "stripe_pro_price_eur_cents", 2900)
    assert pro_checkout_ready() is True


def test_pro_checkout_ready_false_without_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing Stripe secret disables Pro checkout."""

    monkeypatch.setattr(
        "app.application.services.pro_subscription_checkout.stripe_checkout_ready",
        lambda: False,
    )
    monkeypatch.setattr(settings, "stripe_pro_price_id", "price_test_pro")
    assert pro_checkout_ready() is False


@pytest.mark.asyncio
async def test_complete_pro_subscription_sets_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    """Webhook completion upgrades tenant subscription to Pro."""

    tenant_id = "11111111-1111-1111-1111-111111111111"
    subscription = SimpleNamespace(
        tier="free",
        status="active",
        stripe_customer_id=None,
        stripe_subscription_id=None,
        period_end_at=None,
        billing_cycle_anchor=None,
        updated_at=None,
    )

    checkout = SimpleNamespace(
        metadata={"queenswarm_checkout": CHECKOUT_KIND_PRO, "tenant_id": tenant_id},
        customer="cus_test",
        subscription="sub_test",
    )
    stripe_sub = SimpleNamespace(current_period_end=1_900_000_000, billing_cycle_anchor=1_800_000_000)

    mock_session = MagicMock()
    mock_session.flush = AsyncMock()

    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.retrieve.return_value = checkout
    mock_stripe.Subscription.retrieve.return_value = stripe_sub

    async def fake_ensure(_session: object, *, tenant_id: object) -> SimpleNamespace:
        return subscription

    monkeypatch.setattr(
        "app.application.services.pro_subscription_checkout.ensure_tenant_subscription",
        fake_ensure,
    )
    monkeypatch.setattr(
        "app.application.services.pro_subscription_checkout.stripe_effective_secret_key",
        lambda: "sk_test",
    )

    with patch.dict("sys.modules", {"stripe": mock_stripe}):
        upgraded = await complete_pro_subscription_from_stripe(
            mock_session,
            checkout_session_id="cs_test",
            stripe_customer_id="cus_test",
            stripe_subscription_id="sub_test",
        )

    assert upgraded is True
    assert subscription.tier == "pro"
    assert subscription.stripe_customer_id == "cus_test"
    assert subscription.stripe_subscription_id == "sub_test"


@pytest.mark.asyncio
async def test_complete_pro_subscription_ignores_skill_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skill checkout sessions must not trigger Pro upgrade."""

    checkout = SimpleNamespace(
        metadata={"tenant_id": "11111111-1111-1111-1111-111111111111"},
        customer="cus_test",
        subscription=None,
    )
    mock_stripe = MagicMock()
    mock_stripe.checkout.Session.retrieve.return_value = checkout
    mock_session = MagicMock()

    monkeypatch.setattr(
        "app.application.services.pro_subscription_checkout.stripe_effective_secret_key",
        lambda: "sk_test",
    )

    with patch.dict("sys.modules", {"stripe": mock_stripe}):
        upgraded = await complete_pro_subscription_from_stripe(
            mock_session,
            checkout_session_id="cs_skill",
        )

    assert upgraded is False
