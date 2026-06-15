"""Unit tests for REV1 post-purchase onboarding."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.gumroad_purchase_unlock import GumroadSalePing, parse_gumroad_ping_payload
from app.application.services.purchase_onboarding import (
    build_simulate_proof_artifact,
    compose_post_purchase_email_body,
    onboarding_email_already_sent,
    proof_artifact_bytes,
    send_post_purchase_onboarding,
)


def test_build_simulate_proof_artifact_includes_signature() -> None:
    sale = parse_gumroad_ping_payload(
        {"sale_id": "sale_1", "product_id": "p1", "email": "buyer@test.com"},
    )
    assert sale is not None
    proof = build_simulate_proof_artifact(sale=sale, catalog_slug="hero-skill-7")
    assert proof.product_slug == "hero-skill-7"
    assert proof.simulate_first is True
    assert len(proof.signature) == 32
    assert "letagentscook.org/skills/hero-skill-7" in proof.marketing_url


def test_build_simulate_proof_artifact_reads_scorecard(tmp_path: Path) -> None:
    (tmp_path / "GUMROAD_SCORECARD.md").write_text(
        "# Scorecard\n\nReady: **1/1**\n\n- `hero-skill-7` — 100/100 ready (skill)\n",
        encoding="utf-8",
    )
    sale = GumroadSalePing(sale_id="s1", product_id="p1", buyer_email="a@b.c")
    proof = build_simulate_proof_artifact(sale=sale, catalog_slug="hero-skill-7", export_root=tmp_path)
    assert proof.scorecard_score == 100
    assert proof.scorecard_verdict == "ready"


def test_compose_post_purchase_email_body_mentions_simulate_first() -> None:
    sale = GumroadSalePing(sale_id="s1", product_id="p1", product_name="Hero Skill", buyer_email="a@b.c")
    proof = build_simulate_proof_artifact(sale=sale, catalog_slug="hero-skill-7")
    body = compose_post_purchase_email_body(sale=sale, proof=proof)
    assert "simulate-first" in body.lower()
    assert proof.marketing_url in body


def test_proof_artifact_bytes_is_valid_json() -> None:
    sale = GumroadSalePing(sale_id="s1", product_id="p1", buyer_email="a@b.c")
    proof = build_simulate_proof_artifact(sale=sale, catalog_slug="hero-skill-7")
    raw = proof_artifact_bytes(proof)
    assert b'"product_slug": "hero-skill-7"' in raw


@pytest.mark.asyncio
async def test_onboarding_email_already_sent_uses_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.purchase_onboarding.get_json",
        AsyncMock(return_value={"sent": True}),
    )
    assert await onboarding_email_already_sent("sale_x") is True


@pytest.mark.asyncio
async def test_send_post_purchase_onboarding_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "gumroad_post_purchase_onboarding_enabled", False)
    sale = GumroadSalePing(sale_id="s1", product_id="p1", buyer_email="buyer@test.com")
    result = await send_post_purchase_onboarding(sale, catalog_slug="hero-skill-7")
    assert result.skipped is True


@pytest.mark.asyncio
async def test_send_post_purchase_onboarding_sends_email(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "gumroad_post_purchase_onboarding_enabled", True)
    monkeypatch.setattr(
        "app.application.services.purchase_onboarding.get_json",
        AsyncMock(return_value=None),
    )
    mark = AsyncMock()
    monkeypatch.setattr("app.application.services.purchase_onboarding.set_json", mark)
    notify = AsyncMock(return_value=True)
    monkeypatch.setattr("app.application.services.purchase_onboarding.notify_email", notify)

    sale = GumroadSalePing(sale_id="sale_rev1", product_id="p1", buyer_email="buyer@test.com")
    result = await send_post_purchase_onboarding(sale, catalog_slug="hero-skill-7")

    assert result.sent is True
    notify.assert_awaited_once()
    assert notify.await_args.kwargs["to_email"] == "buyer@test.com"
    assert notify.await_args.kwargs["attachment_filename"].endswith(".json")
    mark.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_gumroad_webhook_triggers_onboarding(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "commerce_webhooks_enabled", True)
    monkeypatch.setattr(config.settings, "gumroad_purchase_unlock_enabled", False)
    monkeypatch.setattr(config.settings, "gumroad_post_purchase_onboarding_enabled", True)

    session = AsyncMock()
    ingest = AsyncMock(return_value=True)
    onboarding = AsyncMock(
        return_value=__import__(
            "app.application.services.purchase_onboarding",
            fromlist=["PostPurchaseOnboardingResult"],
        ).PostPurchaseOnboardingResult(sent=True, message="sent"),
    )

    with patch(
        "app.application.services.gumroad_purchase_unlock.ingest_commerce_order_event",
        ingest,
    ), patch(
        "app.application.services.gumroad_purchase_unlock.resolve_slug_for_gumroad_product_id",
        return_value="hero-skill-7",
    ), patch(
        "app.application.services.purchase_onboarding.send_post_purchase_onboarding",
        onboarding,
    ):
        from app.application.services.gumroad_purchase_unlock import process_gumroad_webhook_event

        result = await process_gumroad_webhook_event(
            {"sale_id": "sale_o", "product_id": "prod_o", "email": "buyer@test.com"},
            session=session,
        )

    assert result.ok is True
    assert result.onboarding_sent is True
    onboarding.assert_awaited_once()
