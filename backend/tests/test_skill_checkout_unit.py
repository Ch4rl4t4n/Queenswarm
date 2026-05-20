"""Unit coverage for premium skill checkout helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.skill_marketplace_policy import is_premium_recipe, resolve_skill_price_cents
from app.infrastructure.persistence.models.recipe import Recipe


def test_is_premium_recipe_when_premium_tag_then_true() -> None:
    recipe = Recipe(
        name="x",
        description=None,
        topic_tags=["premium", "api"],
        workflow_template={"steps": []},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )
    assert is_premium_recipe(recipe) is True


def test_is_premium_recipe_when_no_premium_tag_then_false() -> None:
    recipe = Recipe(
        name="x",
        description=None,
        topic_tags=["api"],
        workflow_template={"steps": []},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )
    assert is_premium_recipe(recipe) is False


def test_resolve_skill_price_cents_when_premium_9_tag() -> None:
    recipe = Recipe(
        name="x",
        description=None,
        topic_tags=["premium-9"],
        workflow_template={"steps": []},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )
    assert resolve_skill_price_cents(recipe) == 900


@pytest.mark.asyncio
async def test_create_skill_checkout_resumes_open_pending_session(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock, MagicMock

    from app.application.services.skill_checkout import create_skill_checkout_session

    tenant_id = uuid.uuid4()
    recipe_id = uuid.uuid4()
    purchase_id = uuid.uuid4()
    recipe = Recipe(
        id=recipe_id,
        name="Premium — Newsletter Growth Loop",
        description="test",
        topic_tags=["premium-9"],
        workflow_template={"steps": []},
        success_count=1,
        fail_count=0,
        avg_pollen_earned=1.0,
        verified_at=datetime.now(tz=UTC),
    )
    pending = MagicMock()
    pending.id = purchase_id
    pending.amount_cents = 900
    pending.stripe_checkout_session_id = "cs_test_resume"

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    monkeypatch.setattr(
        "app.application.services.skill_checkout.stripe_checkout_ready",
        lambda: True,
    )
    monkeypatch.setattr(
        "app.application.services.skill_checkout.tenant_has_skill_access",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.skill_checkout._get_pending_purchase",
        AsyncMock(return_value=pending),
    )

    checkout_obj = MagicMock()
    checkout_obj.status = "open"
    checkout_obj.url = "https://checkout.stripe.com/c/pay/cs_test_resume"
    stripe_mod = MagicMock()
    stripe_mod.checkout.Session.retrieve.return_value = checkout_obj
    monkeypatch.setitem(__import__("sys").modules, "stripe", stripe_mod)
    monkeypatch.setattr(
        "app.application.services.skill_checkout.stripe_effective_secret_key",
        lambda: "sk_test_x",
    )

    payload = await create_skill_checkout_session(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=uuid.uuid4(),
        recipe=recipe,
    )

    assert payload["status"] == "checkout_resumed"
    assert payload["checkout_url"].startswith("https://checkout.stripe.com/")
    session.add.assert_not_called()
    stripe_mod.checkout.Session.create.assert_not_called()
