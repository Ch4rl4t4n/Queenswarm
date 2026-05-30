"""Commerce webhook ingress — Stripe checkout/payment events (verify-first, idempotent)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

logger = structlog.get_logger(__name__)

STRIPE_SIGNATURE_TOLERANCE_SEC = 300


class CommerceWebhookResult(BaseModel):
    """Processed webhook outcome."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    event_type: str | None = None
    event_id: str | None = None
    message: str = ""
    ingested: bool = False


def _parse_stripe_signature(header: str) -> tuple[int, list[str]] | None:
    """Parse ``Stripe-Signature`` header into timestamp and v1 signatures."""

    timestamp: int | None = None
    signatures: list[str] = []
    for part in header.split(","):
        chunk = part.strip()
        if chunk.startswith("t="):
            try:
                timestamp = int(chunk[2:])
            except ValueError:
                return None
        elif chunk.startswith("v1="):
            signatures.append(chunk[3:])
    if timestamp is None or not signatures:
        return None
    return timestamp, signatures


def verify_stripe_webhook_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    *,
    tolerance_sec: int = STRIPE_SIGNATURE_TOLERANCE_SEC,
) -> bool:
    """Verify Stripe webhook signature (stdlib HMAC — no stripe SDK required)."""

    if not secret.strip():
        return False
    parsed = _parse_stripe_signature(signature_header)
    if parsed is None:
        return False
    timestamp, signatures = parsed
    if abs(int(time.time()) - timestamp) > tolerance_sec:
        return False
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode()
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in signatures)


async def process_stripe_webhook_event(
    payload: bytes,
    *,
    signature_header: str,
) -> CommerceWebhookResult:
    """Verify and normalize a Stripe webhook event for downstream HiveMind ingest."""

    secret = settings.stripe_webhook_secret.strip()
    if not settings.commerce_webhooks_enabled:
        return CommerceWebhookResult(ok=False, message="Commerce webhooks disabled.")

    if not secret:
        logger.warning("commerce_webhook_stripe_secret_missing")
        return CommerceWebhookResult(ok=False, message="Stripe webhook secret not configured.")

    if not verify_stripe_webhook_signature(payload, signature_header, secret):
        logger.warning("commerce_webhook_stripe_signature_invalid")
        return CommerceWebhookResult(ok=False, message="Invalid Stripe signature.")

    try:
        body: dict[str, Any] = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return CommerceWebhookResult(ok=False, message="Invalid JSON payload.")

    event_type = str(body.get("type") or "")
    event_id = str(body.get("id") or "")
    data_obj = body.get("data") if isinstance(body.get("data"), dict) else {}
    inner = data_obj.get("object") if isinstance(data_obj.get("object"), dict) else {}

    logger.info(
        "commerce_webhook_stripe_received",
        event_type=event_type,
        event_id=event_id,
        object_id=str(inner.get("id") or ""),
    )

    supported = {
        "checkout.session.completed",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "charge.refunded",
    }
    if event_type not in supported:
        return CommerceWebhookResult(
            ok=True,
            event_type=event_type,
            event_id=event_id,
            message="Event acknowledged (unsupported type for auto-ingest).",
            ingested=False,
        )

    return CommerceWebhookResult(
        ok=True,
        event_type=event_type,
        event_id=event_id,
        message="Event verified — queue for HiveMind order sync (operator review).",
        ingested=True,
    )


__all__ = [
    "CommerceWebhookResult",
    "process_stripe_webhook_event",
    "verify_stripe_webhook_signature",
]
