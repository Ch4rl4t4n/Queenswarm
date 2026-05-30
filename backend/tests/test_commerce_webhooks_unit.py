"""Unit tests for commerce webhook verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock

import pytest

from app.application.services.commerce_webhooks import verify_stripe_webhook_signature


def test_verify_stripe_webhook_signature_when_valid_then_true() -> None:
    """Valid HMAC signature passes verification."""

    secret = "whsec_test_secret"
    payload = b'{"id":"evt_123","type":"checkout.session.completed"}'
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={digest}"
    assert verify_stripe_webhook_signature(payload, header, secret) is True


@pytest.mark.asyncio
async def test_process_stripe_webhook_when_disabled_then_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    """Webhook processing respects COMMERCE_WEBHOOKS_ENABLED flag."""

    from app.application.services import commerce_webhooks as mod

    monkeypatch.setattr(mod.settings, "commerce_webhooks_enabled", False)
    result = await mod.process_stripe_webhook_event(b"{}", signature_header="t=1,v1=x")
    assert result.ok is False


@pytest.mark.asyncio
async def test_process_stripe_webhook_when_valid_event_then_ingests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supported Stripe events mark ingested after signature verify."""

    from app.application.services import commerce_webhooks as mod

    secret = "whsec_unit_test"
    monkeypatch.setattr(mod.settings, "commerce_webhooks_enabled", True)
    monkeypatch.setattr(mod.settings, "stripe_webhook_secret", secret)
    ingest = AsyncMock(return_value=True)
    monkeypatch.setattr(mod, "ingest_commerce_order_event", ingest)
    body = json.dumps({"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {"id": "cs_1"}}})
    payload = body.encode()
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    header = f"t={timestamp},v1={digest}"
    result = await mod.process_stripe_webhook_event(payload, signature_header=header)
    assert result.ok is True
    assert result.ingested is True
    assert result.event_type == "checkout.session.completed"
