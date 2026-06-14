"""Unit tests for Gumroad purchase webhook unlock (MK7)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from pathlib import Path

import pytest

from app.application.services.gumroad_purchase_unlock import (
    normalize_gumroad_sale_event,
    parse_gumroad_ping_payload,
    process_gumroad_webhook_event,
    verify_gumroad_webhook_secret,
)


def test_parse_gumroad_ping_payload_when_valid_then_sale() -> None:
    sale = parse_gumroad_ping_payload(
        {
            "sale_id": "sale_1",
            "product_id": "prod_1",
            "email": "Buyer@Example.com",
            "price": "1900",
            "currency": "usd",
        },
    )
    assert sale is not None
    assert sale.sale_id == "sale_1"
    assert sale.buyer_email == "buyer@example.com"
    assert sale.price_cents == 1900


def test_normalize_gumroad_sale_event_provider_is_gumroad() -> None:
    sale = parse_gumroad_ping_payload({"sale_id": "s1", "product_id": "p1", "email": "a@b.c"})
    assert sale is not None
    event = normalize_gumroad_sale_event(sale)
    assert event.provider == "gumroad"
    assert event.event_id == "s1"


def test_parse_gumroad_ping_payload_when_refund_then_flagged() -> None:
    sale = parse_gumroad_ping_payload(
        {"sale_id": "sale_r", "product_id": "prod_r", "refunded": "true", "email": "a@b.c"},
    )
    assert sale is not None
    assert sale.refunded is True
    event = normalize_gumroad_sale_event(sale)
    assert event.event_type == "sale.refunded"


@pytest.mark.asyncio
async def test_sync_gumroad_catalog_from_token_when_api_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.gumroad_catalog_sync import sync_gumroad_catalog_from_token

    async def _empty(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(
        "app.application.services.gumroad_catalog_sync.fetch_gumroad_products",
        _empty,
    )
    result = await sync_gumroad_catalog_from_token(access_token="tok", export_root=Path("/tmp/nope"))
    assert result.ok is False

    assert verify_gumroad_webhook_secret(path_secret="abc", configured_secret="abc") is True
    assert verify_gumroad_webhook_secret(path_secret="wrong", configured_secret="abc") is False


@pytest.mark.asyncio
async def test_process_gumroad_webhook_when_disabled_then_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "commerce_webhooks_enabled", False)
    result = await process_gumroad_webhook_event({"sale_id": "s", "product_id": "p"})
    assert result.ok is False


@pytest.mark.asyncio
async def test_process_gumroad_webhook_when_valid_then_ingests(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "commerce_webhooks_enabled", True)
    monkeypatch.setattr(config.settings, "gumroad_purchase_unlock_enabled", False)
    ingest = AsyncMock(return_value=True)
    with patch(
        "app.application.services.gumroad_purchase_unlock.ingest_commerce_order_event",
        ingest,
    ):
        result = await process_gumroad_webhook_event(
            {"sale_id": "sale_99", "product_id": "prod_99", "email": "x@y.z", "price": "500"},
        )
    assert result.ok is True
    assert result.ingested is True
    ingest.assert_awaited_once()


@pytest.mark.asyncio
async def test_grant_unlock_when_user_and_recipe_match(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.gumroad_purchase_unlock import grant_gumroad_purchase_unlock
    from app.core import config

    monkeypatch.setattr(config.settings, "gumroad_purchase_unlock_enabled", True)
    tenant_id = uuid.uuid4()
    recipe_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), active_tenant_id=tenant_id, email="buyer@test.com")
    recipe = SimpleNamespace(id=recipe_id, name="Hero Skill")

    session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user
    recipe_result = MagicMock()
    recipe_result.scalars.return_value.all.return_value = [recipe]
    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[user_result, recipe_result, dup_result])
    session.add = lambda row: None
    session.flush = AsyncMock()
    session.rollback = AsyncMock()

    sale = parse_gumroad_ping_payload(
        {"sale_id": "sale_x", "product_id": "prod_map", "email": "buyer@test.com", "price": "1900"},
    )
    assert sale is not None

    with patch(
        "app.application.services.gumroad_purchase_unlock.resolve_slug_for_gumroad_product_id",
        return_value="hero-skill",
    ):
        result = await grant_gumroad_purchase_unlock(session, sale=sale)

    assert result.ok is True
    assert result.unlocked is True
    assert result.recipe_id == str(recipe_id)
