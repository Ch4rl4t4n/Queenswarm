"""Unit coverage for Stripe checkout confirmation fallback."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.application.services.skill_checkout import confirm_skill_checkout_session
from app.infrastructure.persistence.models.skill_purchase import SkillPurchase


@pytest.mark.asyncio
async def test_confirm_skill_checkout_unlocks_when_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    purchase_id = uuid.uuid4()
    recipe_id = uuid.uuid4()

    purchase = SkillPurchase(
        id=purchase_id,
        tenant_id=tenant_id,
        dashboard_user_id=uuid.uuid4(),
        recipe_id=recipe_id,
        status="pending",
        amount_cents=1900,
        currency="eur",
        stripe_checkout_session_id="cs_test_123",
    )

    checkout_obj = MagicMock()
    checkout_obj.metadata = {"tenant_id": str(tenant_id)}
    checkout_obj.payment_status = "paid"
    checkout_obj.payment_intent = "pi_test"

    stripe_mod = MagicMock()
    stripe_mod.checkout.Session.retrieve.return_value = checkout_obj
    monkeypatch.setitem(__import__("sys").modules, "stripe", stripe_mod)
    monkeypatch.setattr(
        "app.application.services.skill_checkout.stripe_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.application.services.skill_checkout.settings.stripe_secret_key",
        "sk_test_x",
    )

    session = AsyncMock()
    complete = AsyncMock(return_value=purchase)
    monkeypatch.setattr(
        "app.application.services.skill_checkout.complete_skill_purchase_from_stripe",
        complete,
    )

    payload = await confirm_skill_checkout_session(
        session,
        tenant_id=tenant_id,
        checkout_session_id="cs_test_123",
    )

    assert payload["status"] == "unlocked"
    assert payload["recipe_id"] == str(recipe_id)
    complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_skill_checkout_rejects_tenant_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    checkout_obj = MagicMock()
    checkout_obj.metadata = {"tenant_id": str(uuid.uuid4())}
    checkout_obj.payment_status = "paid"

    stripe_mod = MagicMock()
    stripe_mod.checkout.Session.retrieve.return_value = checkout_obj
    monkeypatch.setitem(__import__("sys").modules, "stripe", stripe_mod)
    monkeypatch.setattr(
        "app.application.services.skill_checkout.stripe_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.application.services.skill_checkout.settings.stripe_secret_key",
        "sk_test_x",
    )

    session = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await confirm_skill_checkout_session(
            session,
            tenant_id=uuid.uuid4(),
            checkout_session_id="cs_test_456",
        )
    assert exc.value.status_code == 403
