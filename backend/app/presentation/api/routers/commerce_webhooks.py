"""Commerce webhook ingress — Stripe (no JWT; signature verified)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.application.services.commerce_webhooks import process_stripe_webhook_event
from app.application.services.gumroad_purchase_unlock import (
    process_gumroad_webhook_event,
    verify_gumroad_webhook_secret,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession

router = APIRouter(prefix="/commerce/webhooks", tags=["Commerce webhooks"])


@router.post(
    "/stripe",
    summary="Stripe webhook ingress (signature verified)",
    include_in_schema=settings.commerce_webhooks_enabled,
)
async def stripe_webhook_ingress(
    request: Request,
    db: DbSession,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, str | bool | None]:
    """Accept Stripe webhook events — verify signature, normalize for order sync."""

    if not settings.commerce_webhooks_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commerce webhooks disabled.")

    stripe_signature = stripe_signature or request.headers.get("Stripe-Signature")
    if not stripe_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header.")

    payload = await request.body()
    result = await process_stripe_webhook_event(payload, signature_header=stripe_signature, session=db)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    await db.commit()

    return {
        "ok": result.ok,
        "event_type": result.event_type,
        "event_id": result.event_id,
        "ingested": result.ingested,
        "message": result.message,
    }


@router.post(
    "/gumroad/{webhook_secret}",
    summary="Gumroad ping webhook (path secret verified)",
    include_in_schema=settings.commerce_webhooks_enabled,
)
async def gumroad_webhook_ingress(
    webhook_secret: str,
    request: Request,
    db: DbSession,
) -> dict[str, str | bool | None]:
    """Accept Gumroad sale ping — verify path secret, ingest order, optional unlock."""

    if not settings.commerce_webhooks_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Commerce webhooks disabled.")

    configured = (settings.gumroad_webhook_secret or "").strip()
    if not configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Gumroad webhook secret not configured.")

    if not verify_gumroad_webhook_secret(path_secret=webhook_secret, configured_secret=configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")

    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload.") from exc
        payload: dict[str, Any] = body if isinstance(body, dict) else {}
    else:
        form = await request.form()
        payload = {str(key): str(value) for key, value in form.multi_items()}

    result = await process_gumroad_webhook_event(payload, session=db)
    if not result.ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)

    await db.commit()

    return {
        "ok": result.ok,
        "sale_id": result.sale_id,
        "ingested": result.ingested,
        "unlocked": result.unlocked,
        "recipe_id": result.recipe_id,
        "tenant_id": result.tenant_id,
        "message": result.message,
    }
