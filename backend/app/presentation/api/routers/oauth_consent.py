"""Hosted OAuth consent HTTP surface (Phase 4.0) — PKCE + Redis state + vault + Dynamic Hub."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from app.presentation.api.deps import DashboardSession, DbSession
from app.application.services.oauth_consent.providers import oauth_catalog_snapshot
from app.application.services.oauth_consent.service import complete_oauth_callback, start_oauth_authorization
from app.core.config import get_settings

router = APIRouter(prefix="/oauth", tags=["OAuth Consent"])

__all__ = ["router"]


def _callback_client_host(request: Request) -> str:
    """Prefer ``X-Forwarded-For`` first hop when Next.js relays the vendor redirect."""

    raw = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if isinstance(raw, str) and raw.strip():
        return raw.split(",")[0].strip()
    solo = request.headers.get("x-real-ip") or request.headers.get("X-Real-IP")
    if isinstance(solo, str) and solo.strip():
        return solo.strip()
    return request.client.host if request.client else "unknown"


class OAuthStartBody(BaseModel):
    """Begin Authorization Code flow for a registered Phase 3 OAuth surface."""

    model_config = {"extra": "ignore"}

    provider: str = Field(..., min_length=4, max_length=72, description="Registry key e.g. google_gmail.")


class OAuthStartResponse(BaseModel):
    """Vendor authorize URL plus opaque state echoed into HttpOnly cookie by Next.js."""

    authorization_url: str
    state: str


class OAuthCallbackResponse(BaseModel):
    """Next.js redirects the browser to ``redirect_url`` (dashboard connectors cockpit)."""

    redirect_url: str


@router.get("/providers", summary="OAuth surfaces + vendor configuration flags")
async def list_oauth_providers(sess: DashboardSession) -> dict[str, object]:
    """Enumerate OAuth consent targets — requires dashboard JWT to reduce idle probing."""

    _ = sess
    return oauth_catalog_snapshot(get_settings())


@router.post("/start", summary="Mint PKCE + Redis state; returns vendor authorize URL")
async def post_oauth_start(sess: DashboardSession, body: OAuthStartBody) -> OAuthStartResponse:
    """Start OAuth Authorization Code flow bound to the authenticated dashboard operator."""

    settings = get_settings()
    try:
        payload = await start_oauth_authorization(
            settings=settings,
            provider_key=body.provider.strip(),
            dashboard_sub=str(sess.get("sub") or ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return OAuthStartResponse.model_validate(payload)


@router.get("/callback", summary="Exchange OAuth code (server-to-server from Next.js)")
async def get_oauth_callback(
    request: Request,
    db: DbSession,
    code: str | None = Query(None),
    state: str | None = Query(None),
    error: str | None = Query(None),
    error_description: str | None = Query(None),
) -> OAuthCallbackResponse:
    """Complete OAuth redirect — **no dashboard JWT**; identity restored from Redis-bound state."""

    settings = get_settings()
    host = _callback_client_host(request)
    oauth_error: str | None = None
    if isinstance(error_description, str) and error_description.strip():
        oauth_error = error_description.strip()
    elif isinstance(error, str) and error.strip():
        oauth_error = error.strip()
    url = await complete_oauth_callback(
        db,
        settings=settings,
        client_host=host,
        code=code,
        state=state,
        oauth_error=oauth_error,
    )
    return OAuthCallbackResponse(redirect_url=url)
