"""Hosted OAuth consent HTTP surface (Phase 4.0) — PKCE + Redis state + vault + Dynamic Hub."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.application.services.session_policy_config import resolve_effective_session_policy
from app.common.http.security_headers import apply_no_store_cache_headers, no_store_cache_headers
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DashboardSession, DbSession
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit
from app.application.services.oauth_consent.providers import oauth_catalog_snapshot
from app.application.services.oauth_consent.service import complete_oauth_callback, start_oauth_authorization
from app.core.config import get_settings

router = APIRouter(prefix="/oauth", tags=["OAuth Consent"])

__all__ = ["router"]


def _callback_client_host(request: Request) -> str:
    """Resolve callback peer label using the shared rate-limit proxy trust policy."""

    return peer_ip_for_rate_limit(request)


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
async def list_oauth_providers(sess: DashboardSession, response: Response) -> dict[str, object]:
    """Enumerate OAuth consent targets — requires dashboard JWT to reduce idle probing."""

    _ = sess
    apply_no_store_cache_headers(response)
    return oauth_catalog_snapshot(get_settings())


@router.post("/start", summary="Mint PKCE + Redis state; returns vendor authorize URL")
async def post_oauth_start(
    sess: DashboardSession,
    db: DbSession,
    body: OAuthStartBody,
    response: Response,
) -> OAuthStartResponse:
    """Start OAuth Authorization Code flow bound to the authenticated dashboard operator."""

    settings = get_settings()
    oauth_ttl = int(settings.oauth_state_ttl_sec)
    tenant_claim = sess.get("tenant_id")
    if isinstance(tenant_claim, str) and tenant_claim.strip():
        try:
            tenant = await db.get(Tenant, uuid.UUID(tenant_claim.strip()))
        except ValueError:
            tenant = None
        if tenant is not None:
            effective = resolve_effective_session_policy(tenant)
            if not bool(effective.get("oauth_pkce_enabled", True)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="OAuth PKCE disabled for this tenant.",
                    headers=no_store_cache_headers(),
                )
            oauth_ttl = int(effective["oauth_state_ttl_sec"])
    try:
        payload = await start_oauth_authorization(
            settings=settings,
            provider_key=body.provider.strip(),
            dashboard_sub=str(sess.get("sub") or ""),
            oauth_state_ttl_sec=oauth_ttl,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            headers=no_store_cache_headers(),
        ) from exc
    apply_no_store_cache_headers(response)
    return OAuthStartResponse.model_validate(payload)


@router.get("/callback", summary="Exchange OAuth code (server-to-server from Next.js)")
async def get_oauth_callback(
    request: Request,
    db: DbSession,
    response: Response,
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
    apply_no_store_cache_headers(response)
    return OAuthCallbackResponse(redirect_url=url)
