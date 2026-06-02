"""OAuth authorization start + callback completion (PKCE, Redis state, vault + Dynamic Hub)."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
import uuid
from typing import Any
from urllib.parse import quote, urlencode

import httpx
from jose import jwt as jose_jwt
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.oauth_consent.providers import (
    OAUTH_SURFACES,
    OAuthSurfaceSpec,
    client_credentials_for_family,
)
from app.core.config import Settings
from app.core.logging import get_logger
from app.core.redis_client import get_json, redis_delete, set_json, sliding_window_reserve
from app.domain.external.hive_audit import mirror_external_audit_to_vault
from app.infrastructure.connectors.dynamic.schemas import (
    DynamicConnectorCreateBody,
    DynamicConnectorPatchBody,
    DynamicConnectorSecretsInbound,
)
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.phase3.catalog import get_phase3_template
from app.infrastructure.connectors.secure_vault import CredentialPayload, vault_upsert_credential
from app.infrastructure.persistence.models.connector_vault_entry import ConnectorVaultEntry
from app.core.jwt_tokens import parse_dashboard_user_subject

logger = get_logger(__name__)

_STATE_NS = "oauth_consent:v1:"


def oauth_state_redis_key(state: str) -> str:
    """Redis key wrapping opaque OAuth ``state``."""

    return f"{_STATE_NS}{state.strip()}"


async def _vault_slug_owned_or_free(db: AsyncSession, *, slug: str, user_id: uuid.UUID) -> bool:
    """Return False when another dashboard user already owns this vault slug."""

    stmt = select(ConnectorVaultEntry).where(ConnectorVaultEntry.slug == slug.strip().lower()).limit(1)
    row = await db.scalar(stmt)
    if row is None:
        return True
    return row.dashboard_user_id == user_id


def pkce_pair() -> tuple[str, str]:
    """Return ``(code_verifier, code_challenge)`` for S256 PKCE."""

    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


def _frontend_redirect(settings: Settings, *, ok: bool, provider_key: str | None = None, reason: str | None = None) -> str:
    """Return absolute dashboard URL under ``oauth_public_origin``."""

    base = settings.oauth_public_origin
    if ok:
        pk = quote(provider_key or "", safe="")
        return f"{base}/integrations?tab=studio&oauth=success&provider={pk}"
    detail = quote(reason or "unknown", safe="")
    return f"{base}/integrations?tab=studio&oauth=error&reason={detail}"


def _build_authorize_url(
    spec: OAuthSurfaceSpec,
    *,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str | None,
    nonce: str,
    meta_config_id: str | None = None,
) -> str:
    """Compose vendor authorize URL with PKCE + OIDC nonce where applicable."""

    params: dict[str, str] = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if spec.vendor_family == "meta" and meta_config_id:
        params["config_id"] = meta_config_id
        params["override_default_response_type"] = "true"
    if spec.provider_key == "instagram_graph":
        # Do NOT send IG_API_ONBOARDING — Meta dialog returns "Something Went Wrong" (community #536420708641817).
        pass
    if spec.vendor_family == "tiktok":
        params["client_key"] = client_id
    else:
        params["client_id"] = client_id
    if spec.scopes:
        if spec.vendor_family in {"meta", "tiktok"}:
            params["scope"] = ",".join(spec.scopes)
        else:
            params["scope"] = " ".join(spec.scopes)
    if spec.uses_pkce and code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    if spec.google_offline_prompt:
        params["access_type"] = "offline"
        params["prompt"] = "consent"
    if spec.notion_owner_user:
        params["owner"] = "user"
    if spec.vendor_family in {"google", "microsoft"}:
        params["nonce"] = nonce
    if spec.vendor_family == "x":
        # X authorize rejects ``+``-joined scopes from default urlencode — use %20.
        query = urlencode(params, quote_via=quote)
    else:
        query = urlencode(params)
    return f"{spec.authorize_url}?{query}"


def _verify_oidc_nonce(*, id_token: str | None, expected_nonce: str | None, vendor_family: str) -> None:
    """Best-effort nonce compare on OIDC id_token (signature verified by TLS + issuer in MVP)."""

    if vendor_family not in {"google", "microsoft"}:
        return
    if not expected_nonce:
        return
    if not id_token:
        return
    claims = jose_jwt.get_unverified_claims(id_token)
    if claims.get("nonce") != expected_nonce:
        msg = "OAuth OIDC nonce mismatch."
        raise ValueError(msg)


async def _exchange_authorization_code(
    spec: OAuthSurfaceSpec,
    *,
    settings: Settings,
    code: str,
    redirect_uri: str,
    code_verifier: str | None,
) -> dict[str, Any]:
    """Exchange authorization code at vendor token endpoint."""

    cid, csec = client_credentials_for_family(settings, spec.vendor_family)
    headers: dict[str, str] = {}
    if spec.vendor_family == "github":
        headers["Accept"] = "application/json"

    if spec.vendor_family == "notion":
        basic = base64.b64encode(f"{cid}:{csec}".encode()).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"
        headers["Content-Type"] = "application/json"
        payload = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(spec.token_url, headers=headers, json=payload)
    elif spec.vendor_family == "x":
        if not code_verifier:
            msg = "x_oauth_requires_pkce_verifier"
            raise ValueError(msg)
        from urllib.parse import quote

        basic = base64.b64encode(f"{quote(cid, safe='')}:{quote(csec, safe='')}".encode()).decode("ascii")
        headers["Authorization"] = f"Basic {basic}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(spec.token_url, data=form, headers=headers)
    elif spec.vendor_family == "tiktok":
        if not code_verifier:
            msg = "tiktok_oauth_requires_pkce_verifier"
            raise ValueError(msg)
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        form = {
            "client_key": cid,
            "client_secret": csec,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(spec.token_url, data=form, headers=headers)
    else:
        form: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": cid,
            "client_secret": csec,
        }
        if spec.uses_pkce and code_verifier:
            form["code_verifier"] = code_verifier
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(spec.token_url, data=form, headers=headers)

    if resp.status_code >= 400:
        msg = f"token_exchange_failed_http_{resp.status_code}"
        raise ValueError(msg)

    if spec.vendor_family == "github":
        payload = resp.json()
    else:
        try:
            payload = resp.json()
        except Exception as exc:  # noqa: BLE001 — normalize vendor quirks
            raise ValueError("token_response_not_json") from exc

    if not isinstance(payload, dict):
        msg = "token_response_invalid_shape"
        raise ValueError(msg)
    if spec.vendor_family == "tiktok":
        data_block = payload.get("data")
        if isinstance(data_block, dict):
            payload = {**payload, **data_block}
    err = payload.get("error")
    if isinstance(err, str) and err.strip():
        desc = payload.get("error_description") or err
        raise ValueError(str(desc))

    access = payload.get("access_token")
    if not isinstance(access, str) or not access.strip():
        msg = "missing_access_token"
        raise ValueError(msg)

    refresh = payload.get("refresh_token")
    refresh_txt = refresh.strip() if isinstance(refresh, str) and refresh.strip() else None
    id_token = payload.get("id_token")
    id_txt = id_token.strip() if isinstance(id_token, str) and id_token.strip() else None
    expires = payload.get("expires_in")
    exp_int = int(expires) if isinstance(expires, (int, float)) else None

    return {
        "access_token": access.strip(),
        "refresh_token": refresh_txt,
        "id_token": id_txt,
        "expires_in": exp_int,
    }


async def _exchange_meta_long_lived_token(
    *,
    settings: Settings,
    short_lived_token: str,
) -> str:
    """Exchange Meta short-lived user token for ~60-day long-lived token."""

    cid, csec = client_credentials_for_family(settings, "meta")
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": cid,
        "client_secret": csec,
        "fb_exchange_token": short_lived_token.strip(),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get("https://graph.facebook.com/v21.0/oauth/access_token", params=params)
    if resp.status_code >= 400:
        msg = f"meta_long_lived_exchange_http_{resp.status_code}"
        raise ValueError(msg)
    payload = resp.json()
    if not isinstance(payload, dict):
        msg = "meta_long_lived_response_invalid"
        raise ValueError(msg)
    access = payload.get("access_token")
    if not isinstance(access, str) or not access.strip():
        msg = "meta_long_lived_missing_access_token"
        raise ValueError(msg)
    return access.strip()


async def _mirror_audit(
    *,
    settings: Settings,
    provider_key: str,
    ok: bool,
    latency_ms: int,
    summary: dict[str, Any],
    task_id: str,
) -> None:
    """Hive Mind Markdown audit (fail-open)."""

    await mirror_external_audit_to_vault(
        project_slug=f"oauth_{provider_key}",
        action_slug="oauth_consent_callback",
        ok=ok,
        latency_ms=latency_ms,
        summary=summary,
        agent_id="oauth_consent_service",
        swarm_id="connector_hub",
        task_id=task_id,
        settings=settings,
    )


async def start_oauth_authorization(
    *,
    settings: Settings,
    provider_key: str,
    dashboard_sub: str,
    oauth_state_ttl_sec: int | None = None,
) -> dict[str, str]:
    """Mint Redis-bound state + PKCE verifier and return the vendor authorization URL."""

    cleaned_sub = dashboard_sub.strip()
    user_uuid = parse_dashboard_user_subject(cleaned_sub)
    if user_uuid is None:
        msg = "malformed_dashboard_subject"
        raise ValueError(msg)

    spec = OAUTH_SURFACES.get(provider_key.strip())
    if spec is None:
        msg = "unknown_oauth_provider"
        raise ValueError(msg)

    cid, csec = client_credentials_for_family(settings, spec.vendor_family)
    if not cid or not csec:
        msg = "oauth_client_not_configured"
        raise ValueError(msg)

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(24)
    verifier: str | None = None
    challenge: str | None = None
    if spec.uses_pkce:
        verifier, challenge = pkce_pair()

    blob: dict[str, Any] = {
        "provider_key": spec.provider_key,
        "nonce": nonce,
        "user_uuid": str(user_uuid),
        "dashboard_sub": cleaned_sub,
        "code_verifier": verifier or "",
    }
    ttl = int(oauth_state_ttl_sec if oauth_state_ttl_sec is not None else settings.oauth_state_ttl_sec)
    await set_json(oauth_state_redis_key(state), blob, ttl=ttl)

    redirect_uri = settings.oauth_redirect_uri
    meta_config_id = settings.oauth_meta_config_id.strip() if spec.vendor_family == "meta" else ""
    authorize = _build_authorize_url(
        spec,
        client_id=cid,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=challenge,
        nonce=nonce,
        meta_config_id=meta_config_id or None,
    )
    logger.info(
        "oauth_consent.start",
        agent_id=str(user_uuid),
        swarm_id=spec.provider_key,
        task_id=state[:16],
    )
    return {"authorization_url": authorize, "state": state}


async def complete_oauth_callback(
    db: AsyncSession,
    *,
    settings: Settings,
    client_host: str,
    code: str | None,
    state: str | None,
    oauth_error: str | None,
) -> str:
    """Validate Redis state, exchange tokens, seal vault + Dynamic Hub row, return frontend redirect URL."""

    started = time.perf_counter()
    audit_task = secrets.token_hex(8)
    host = client_host.strip() or "unknown"

    bucket = f"oauth_cb:v1:{host}"
    try:
        allowed = await sliding_window_reserve(
            bucket,
            limit=int(settings.oauth_callback_rate_per_ip),
            window_sec=float(settings.oauth_callback_rate_window_sec),
        )
    except RedisError as exc:
        logger.warning(
            "oauth_consent.callback.ratelimit_redis_degraded",
            agent_id="oauth_consent",
            swarm_id="",
            task_id=audit_task,
            error=str(exc),
            host=host,
        )
        allowed = True
    if not allowed:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key="unknown",
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "rate_limited", "host": host},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="rate_limited")

    if oauth_error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key="unknown",
            ok=False,
            latency_ms=latency_ms,
            summary={"vendor_error": oauth_error, "host": host},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason=oauth_error)

    if not code or not state:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key="unknown",
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "missing_code_or_state"},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="missing_code_or_state")

    key = oauth_state_redis_key(state)
    blob = await get_json(key)
    await redis_delete(key)
    if blob is None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key="unknown",
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "state_expired_or_replay"},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="invalid_state")

    pk = str(blob.get("provider_key") or "")
    spec = OAUTH_SURFACES.get(pk)
    if spec is None:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk or "unknown",
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "unknown_provider_in_state"},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="invalid_state")

    try:
        uid = uuid.UUID(str(blob.get("user_uuid")))
    except (TypeError, ValueError):
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "malformed_user_in_state"},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="invalid_state")

    verifier_raw = blob.get("code_verifier")
    verifier = str(verifier_raw).strip() if verifier_raw else None
    if spec.uses_pkce and not verifier:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "missing_pkce_verifier"},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="pkce_missing")

    nonce_expected = str(blob.get("nonce") or "").strip() or None

    try:
        tokens = await _exchange_authorization_code(
            spec,
            settings=settings,
            code=code.strip(),
            redirect_uri=settings.oauth_redirect_uri,
            code_verifier=verifier,
        )
        if spec.vendor_family == "meta":
            try:
                long_lived = await _exchange_meta_long_lived_token(
                    settings=settings,
                    short_lived_token=str(tokens["access_token"]),
                )
                tokens["access_token"] = long_lived
            except ValueError as meta_exc:
                logger.warning(
                    "oauth_consent.meta_long_lived_fallback",
                    agent_id=str(uid),
                    swarm_id=pk,
                    task_id=audit_task,
                    error=str(meta_exc),
                )
        _verify_oidc_nonce(
            id_token=tokens.get("id_token") if isinstance(tokens.get("id_token"), str) else None,
            expected_nonce=nonce_expected,
            vendor_family=spec.vendor_family,
        )
    except ValueError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "token_exchange_failed", "detail": str(exc)},
            task_id=audit_task,
        )
        logger.warning(
            "oauth_consent.exchange_failed",
            agent_id=str(uid),
            swarm_id=pk,
            task_id=audit_task,
            error=str(exc),
        )
        return _frontend_redirect(settings, ok=False, reason="token_exchange_failed")

    cid, csec = client_credentials_for_family(settings, spec.vendor_family)
    tpl = get_phase3_template(spec.template_id)
    vault_slug = tpl.suggested_slug.strip().lower()

    if not await _vault_slug_owned_or_free(db, slug=vault_slug, user_id=uid):
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "vault_slug_owned_by_other_user", "slug": vault_slug},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="vault_slug_conflict")

    cred = CredentialPayload(
        kind="oauth2",
        oauth2_access_token=str(tokens["access_token"]),
        oauth2_refresh_token=tokens.get("refresh_token"),
        oauth2_token_endpoint=spec.token_url,
        oauth2_client_id=cid,
        oauth2_client_secret=csec,
        scopes=tuple(spec.scopes),
    )

    try:
        from app.infrastructure.persistence.models.dashboard_user import DashboardUser

        dashboard_user = await db.get(DashboardUser, uid)
        tenant_id = dashboard_user.active_tenant_id if dashboard_user is not None else None
        await vault_upsert_credential(
            db,
            slug=vault_slug,
            user_id=uid,
            payload=cred,
            label=spec.label,
            tenant_id=tenant_id,
        )
    except Exception as exc:  # noqa: BLE001 — redirect operator with error
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "vault_upsert_failed", "detail": str(exc)},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="vault_failed")

    secrets_inbound = DynamicConnectorSecretsInbound(
        oauth2_access_token=str(tokens["access_token"]),
        oauth2_refresh_token=tokens.get("refresh_token"),
        oauth2_token_endpoint=spec.token_url,
        oauth2_client_id=cid,
        oauth2_client_secret=csec,
    )

    from app.application.services.social_connected_accounts import SOCIAL_OAUTH_PROVIDER_KEYS, upsert_accounts_from_oauth

    is_social_oauth = pk in SOCIAL_OAUTH_PROVIDER_KEYS
    try:
        if is_social_oauth:
            await _ensure_oauth_connector_template(
                db,
                user_id=uid,
                spec=spec,
                tpl_slug=vault_slug,
                tpl_title=tpl.title,
                base_url=tpl.base_url,
                manager_slugs=tuple(tpl.suggested_manager_slugs),
                tools=tuple(tpl.tools),
            )
            from app.infrastructure.persistence.models.dashboard_user import DashboardUser

            dashboard_user = await db.get(DashboardUser, uid)
            if dashboard_user is not None and dashboard_user.active_tenant_id is not None:
                await upsert_accounts_from_oauth(
                    db,
                    tenant_id=dashboard_user.active_tenant_id,
                    dashboard_user_id=uid,
                    spec=spec,
                    secrets=secrets_inbound,
                    access_token=str(tokens["access_token"]),
                    settings=settings,
                )
        else:
            await _upsert_dynamic_hub_oauth(
                db,
                user_id=uid,
                spec=spec,
                tpl_slug=vault_slug,
                tpl_title=tpl.title,
                base_url=tpl.base_url,
                manager_slugs=tuple(tpl.suggested_manager_slugs),
                tools=tuple(tpl.tools),
                secrets=secrets_inbound,
            )
    except ValueError as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "hub_conflict", "detail": str(exc)},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="hub_slug_conflict")
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        await _mirror_audit(
            settings=settings,
            provider_key=pk,
            ok=False,
            latency_ms=latency_ms,
            summary={"reason": "hub_persist_failed", "detail": str(exc)},
            task_id=audit_task,
        )
        return _frontend_redirect(settings, ok=False, reason="hub_failed")

    latency_ms = int((time.perf_counter() - started) * 1000)
    await _mirror_audit(
        settings=settings,
        provider_key=pk,
        ok=True,
        latency_ms=latency_ms,
        summary={"vault_slug": vault_slug, "host": host},
        task_id=audit_task,
    )
    logger.info(
        "oauth_consent.completed",
        agent_id=str(uid),
        swarm_id=pk,
        task_id=audit_task,
    )
    await _post_oauth_virtual_company_sync(db, user_id=uid)
    return _frontend_redirect(settings, ok=True, provider_key=pk)


async def _ensure_oauth_connector_template(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    spec: OAuthSurfaceSpec,
    tpl_slug: str,
    tpl_title: str,
    base_url: str | None,
    manager_slugs: tuple[str, ...],
    tools: tuple[dict[str, Any], ...],
) -> None:
    """Install OAuth connector manifest without overwriting per-account social tokens."""

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(db, slug=tpl_slug)
    manifest = {"tools": [dict(tool) for tool in tools]}
    if row is None:
        body = DynamicConnectorCreateBody(
            slug=tpl_slug,
            display_name=tpl_title,
            base_url=base_url,
            auth_type="oauth2",
            allowed_manager_slugs=list(manager_slugs),
            mcp_manifest=manifest,
            secrets=None,
        )
        await svc.create_row(db, dashboard_user_id=user_id, body=body)
        await _activate_oauth_connector_row(db, tpl_slug=tpl_slug)
        return

    if row.is_builtin:
        return

    if row.dashboard_user_id != user_id:
        msg = "connector slug already registered for a different dashboard user."
        raise ValueError(msg)

    if not row.is_active:
        row.is_active = True
        await db.flush()


async def _upsert_dynamic_hub_oauth(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    spec: OAuthSurfaceSpec,
    tpl_slug: str,
    tpl_title: str,
    base_url: str | None,
    manager_slugs: tuple[str, ...],
    tools: tuple[dict[str, Any], ...],
    secrets: DynamicConnectorSecretsInbound,
) -> None:
    """Create or patch a Dynamic Hub row with oauth2 ciphertext aligned to Phase 3 template."""

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(db, slug=tpl_slug)
    manifest = {"tools": [dict(tool) for tool in tools]}
    if row is None:
        body = DynamicConnectorCreateBody(
            slug=tpl_slug,
            display_name=tpl_title,
            base_url=base_url,
            auth_type="oauth2",
            allowed_manager_slugs=list(manager_slugs),
            mcp_manifest=manifest,
            secrets=secrets,
        )
        await svc.create_row(db, dashboard_user_id=user_id, body=body)
        await _activate_oauth_connector_row(db, tpl_slug=tpl_slug)
        return

    if row.is_builtin:
        # Vault already sealed — skip mutating immutable built-ins sharing slug collisions.
        return

    if row.dashboard_user_id != user_id:
        msg = "connector slug already registered for a different dashboard user."
        raise ValueError(msg)

    patch = DynamicConnectorPatchBody(auth_type="oauth2", secrets=secrets, is_active=True)
    await svc.patch_row(db, connector_id=row.id, dashboard_user_id=user_id, body=patch)


async def _activate_oauth_connector_row(db: AsyncSession, *, tpl_slug: str) -> None:
    """Mark OAuth connector active after successful consent — no HEAD probe required."""

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(db, slug=tpl_slug)
    if row is None or row.is_builtin:
        return
    if row.is_active:
        return
    row.is_active = True
    await db.commit()


async def _post_oauth_virtual_company_sync(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    """After OAuth consent: try activating solo super routers when connectors become ready."""

    from app.application.services.virtual_company_profile import provision_solo_super_routers
    from app.infrastructure.persistence.models.dashboard_user import DashboardUser
    from app.infrastructure.persistence.models.tenant import Tenant

    user = await db.get(DashboardUser, user_id)
    if user is None or user.active_tenant_id is None:
        return
    tenant = await db.get(Tenant, user.active_tenant_id)
    if tenant is None:
        return
    try:
        await provision_solo_super_routers(
            db,
            tenant=tenant,
            dashboard_user_id=user_id,
            activate_when_ready=True,
        )
    except Exception as exc:  # noqa: BLE001 — OAuth redirect must not fail on router sync
        logger.warning(
            "oauth_consent.virtual_company_router_sync_failed",
            agent_id=str(user_id),
            swarm_id="virtual_company",
            task_id="oauth-callback",
            error=str(exc),
        )


__all__ = [
    "complete_oauth_callback",
    "oauth_state_redis_key",
    "pkce_pair",
    "start_oauth_authorization",
]
