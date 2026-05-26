"""Social publish — Phase C multi-channel API."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.services.social_publish import (
    SocialPublishRequestBody,
    SocialPublishResultOut,
    SocialPublishSnapshotOut,
    build_social_publish_snapshot,
    run_social_publish,
)
from app.application.services.social_publish_trusted_auto import (
    TrustedAutoPolicyOut,
    TrustedAutoPolicyPatch,
    build_trusted_auto_policy,
    merge_trusted_auto_patch,
)
from app.application.services.social_connected_accounts import (
    SocialAccountPatchBody,
    SocialConnectedAccountOut,
    SocialConnectedAccountsSnapshotOut,
    account_to_out,
    build_social_accounts_snapshot,
    patch_social_account,
    revoke_social_account,
    set_channel_default,
)
from app.application.services.tiktok_social_context import TikTokAccountSnapshotOut, build_tiktok_account_snapshot
from app.application.services.meta_social_context import MetaAccountsSnapshotOut, build_meta_accounts_snapshot
from app.application.services.x_social_context import XAccountSnapshotOut, build_x_account_snapshot
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.infrastructure.persistence.models.tenant import Tenant

router = APIRouter(prefix="/social-publish", tags=["Social publish"])


def _require_enabled() -> None:
    if not settings.social_publish_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social publish disabled.")


async def _tenant_from_principal(
    db: DbSession,
    principal: dict[str, Any],
) -> Tenant | None:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        return None
    return await db.get(Tenant, tenant_id)


@router.get("", response_model=SocialPublishSnapshotOut, summary="Social publish snapshot")
async def get_social_publish_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SocialPublishSnapshotOut:
    """Channel readiness + approved publish packs — single snapshot for lazy panel."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    snapshot = await build_social_publish_snapshot(
        db,
        dashboard_user_id=user.id,
        tenant=tenant,
    )
    snapshot.enabled = True
    return snapshot


@router.get(
    "/trusted-auto",
    response_model=TrustedAutoPolicyOut,
    summary="Trusted auto-publish policy snapshot",
)
async def get_trusted_auto_policy(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TrustedAutoPolicyOut:
    """Return manual/auto channel modes and simulate history for operator UI."""

    _require_enabled()
    tenant = await _tenant_from_principal(db, principal)
    return build_trusted_auto_policy(tenant)


@router.patch(
    "/trusted-auto",
    response_model=TrustedAutoPolicyOut,
    summary="Update trusted auto-publish policy",
)
async def patch_trusted_auto_policy(
    body: TrustedAutoPolicyPatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TrustedAutoPolicyOut:
    """Persist tenant trusted auto settings (manual vs auto per channel)."""

    _require_enabled()
    tenant = await _tenant_from_principal(db, principal)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    tenant.operator_settings = merge_trusted_auto_patch(tenant.operator_settings, body)
    await db.commit()
    await db.refresh(tenant)
    return build_trusted_auto_policy(tenant)


@router.get(
    "/meta-accounts",
    response_model=MetaAccountsSnapshotOut,
    summary="Meta Pages + Instagram business accounts (OAuth token)",
)
async def get_meta_accounts(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> MetaAccountsSnapshotOut:
    """Discover ig_user_id / page_id after Meta OAuth — for operator copy-paste."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    return await build_meta_accounts_snapshot(
        db,
        dashboard_user_id=user.id,
        oauth_meta_configured=bool(
            settings.oauth_meta_client_id.strip() and settings.oauth_meta_client_secret.strip()
        ),
    )


@router.get(
    "/x-account",
    response_model=XAccountSnapshotOut,
    summary="X (Twitter) authenticated user profile (OAuth token)",
)
async def get_x_account(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> XAccountSnapshotOut:
    """Verify X OAuth and return @username for operator checklist."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    return await build_x_account_snapshot(
        db,
        dashboard_user_id=user.id,
        oauth_x_configured=bool(settings.oauth_x_client_id.strip() and settings.oauth_x_client_secret.strip()),
    )


@router.get(
    "/tiktok-account",
    response_model=TikTokAccountSnapshotOut,
    summary="TikTok creator info (Content Posting API)",
)
async def get_tiktok_account(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> TikTokAccountSnapshotOut:
    """Verify TikTok OAuth and creator publishing capabilities."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    return await build_tiktok_account_snapshot(
        db,
        dashboard_user_id=user.id,
        oauth_tiktok_configured=bool(
            settings.oauth_tiktok_client_key.strip() and settings.oauth_tiktok_client_secret.strip()
        ),
    )


def _publish_context_from_body(body: SocialPublishRequestBody) -> dict[str, str]:
    ctx: dict[str, str] = {}
    if body.ig_user_id.strip():
        ctx["ig_user_id"] = body.ig_user_id.strip()
    if body.page_id.strip():
        ctx["page_id"] = body.page_id.strip()
    return ctx


@router.get(
    "/accounts",
    response_model=SocialConnectedAccountsSnapshotOut,
    summary="List tenant connected social accounts",
)
async def list_connected_social_accounts(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SocialConnectedAccountsSnapshotOut:
    """All OAuth-connected social identities for the active tenant."""

    _require_enabled()
    tenant = await _tenant_from_principal(db, principal)
    return await build_social_accounts_snapshot(db, tenant=tenant)


@router.patch(
    "/accounts/{account_id}",
    response_model=SocialConnectedAccountOut,
    summary="Update connected social account label or default",
)
async def patch_connected_social_account(
    account_id: uuid.UUID,
    body: SocialAccountPatchBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SocialConnectedAccountOut:
    """Rename account or set channel default for automation."""

    _require_enabled()
    tenant = await _tenant_from_principal(db, principal)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    row = await patch_social_account(db, tenant_id=tenant.id, account_id=account_id, body=body)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found.")
    await db.commit()
    await db.refresh(row)
    return account_to_out(row)


@router.post(
    "/accounts/{account_id}/default",
    response_model=SocialConnectedAccountOut,
    summary="Set default social account for its channel",
)
async def set_default_social_account(
    account_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SocialConnectedAccountOut:
    """Mark account as default — used when publish pack omits social_account_id."""

    _require_enabled()
    tenant = await _tenant_from_principal(db, principal)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    row = await set_channel_default(db, tenant_id=tenant.id, account_id=account_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found.")
    await db.commit()
    await db.refresh(row)
    return account_to_out(row)


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke connected social account",
)
async def delete_connected_social_account(
    account_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> None:
    """Revoke account — tokens remain encrypted for audit but publish will not use it."""

    _require_enabled()
    tenant = await _tenant_from_principal(db, principal)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    ok = await revoke_social_account(db, tenant_id=tenant.id, account_id=account_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found.")
    await db.commit()


@router.post(
    "/{deliverable_id}/simulate",
    response_model=SocialPublishResultOut,
    summary="Simulate social publish for approved pack",
)
async def simulate_social_publish(
    deliverable_id: uuid.UUID,
    body: SocialPublishRequestBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SocialPublishResultOut:
    """Dry-run social publish — no live upstream unless connector read probe."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    try:
        result = await run_social_publish(
            db,
            deliverable_id=deliverable_id,
            dashboard_user_id=user.id,
            tenant=tenant,
            mode="simulate",
            channel_override=body.channel,
            social_account_id=body.social_account_id,
            context=_publish_context_from_body(body),
            reviewed_by=str(principal.get("session", {}).get("sub") or ""),
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/{deliverable_id}/publish",
    response_model=SocialPublishResultOut,
    summary="Live social publish (operator confirmed)",
)
async def live_social_publish(
    deliverable_id: uuid.UUID,
    body: SocialPublishRequestBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> SocialPublishResultOut:
    """Live publish — requires SOCIAL_PUBLISH_LIVE_ENABLED and operator_confirmed."""

    _require_enabled()
    user = principal.get("user")
    if user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard user missing.")
    tenant = await _tenant_from_principal(db, principal)
    try:
        result = await run_social_publish(
            db,
            deliverable_id=deliverable_id,
            dashboard_user_id=user.id,
            tenant=tenant,
            mode="live",
            channel_override=body.channel,
            social_account_id=body.social_account_id,
            context=_publish_context_from_body(body),
            operator_confirmed=body.operator_confirmed,
            reviewed_by=str(principal.get("session", {}).get("sub") or ""),
        )
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


__all__ = ["router"]
