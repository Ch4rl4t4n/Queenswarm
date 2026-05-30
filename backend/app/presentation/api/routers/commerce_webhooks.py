"""Commerce webhook ingress — Stripe (no JWT; signature verified)."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.application.services.commerce_webhooks import process_stripe_webhook_event
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
