"""Queen Maintainer API — tech health, routine settings, manual trigger, GitHub webhook."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.application.services.queen_maintainer.post_merge_webhook import (
    PostMergeWebhookConfigError,
    PostMergeWebhookDisabledError,
    decode_github_webhook_payload,
    handle_github_post_merge_webhook,
    verify_github_webhook_signature,
    webhook_status_payload,
)
from app.application.services.queen_maintainer.pr_workflow import (
    build_branch_name,
    create_github_pr_if_configured,
    validate_changed_paths,
)
from app.application.services.queen_maintainer.service import (
    ensure_queen_maintainer_routine,
    queue_maintainer_run,
)
from app.application.services.queen_maintainer.tech_health import build_tech_health_report
from app.application.services.rbac import has_permission
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/queen-maintainer", tags=["Queen Maintainer"])


class QueenMaintainerSettingsResponse(BaseModel):
    enabled: bool
    feature_flag: bool
    routine_id: str | None = None
    github_owner: str = ""
    github_repo: str = ""
    post_merge_webhook: dict[str, Any] = Field(default_factory=dict)


class QueenMaintainerSettingsUpdateBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    enabled: bool


class QueenMaintainerPrDraftBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=256)
    body: str = Field(min_length=10, max_length=65_000)
    slug: str = Field(min_length=2, max_length=48)
    changed_paths: list[str] = Field(default_factory=list)


def _ensure_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"} or not has_permission(role=role, permission="settings:view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin tenant role required.")


@router.get("/tech-health", summary="Read-only tech health report")
async def queen_maintainer_tech_health(
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return repository health signals for Maintainer planning."""

    return build_tech_health_report()


@router.get("/settings", response_model=QueenMaintainerSettingsResponse, summary="Maintainer routine settings")
async def queen_maintainer_settings(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> QueenMaintainerSettingsResponse:
    _ensure_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    row = await db.scalar(
        select(SupervisorRoutine).where(
            SupervisorRoutine.tenant_id == tenant_id,
            SupervisorRoutine.name == "Queen Maintainer — weekly tech health",
        ),
    )
    return QueenMaintainerSettingsResponse(
        enabled=bool(row.is_active) if row is not None else False,
        feature_flag=bool(settings.queen_maintainer_enabled),
        routine_id=str(row.id) if row is not None else None,
        github_owner=settings.queen_maintainer_github_owner,
        github_repo=settings.queen_maintainer_github_repo,
        post_merge_webhook=webhook_status_payload(),
    )


@router.put("/settings", response_model=QueenMaintainerSettingsResponse, summary="Enable/disable Maintainer routine")
async def update_queen_maintainer_settings(
    body: QueenMaintainerSettingsUpdateBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> QueenMaintainerSettingsResponse:
    _ensure_admin(principal)
    if not settings.queen_maintainer_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Queen Maintainer feature flag disabled (QUEEN_MAINTAINER_ENABLED).",
        )
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    subject = f"dashboard:{principal['user'].id}"
    row = await ensure_queen_maintainer_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=subject,
        enabled=body.enabled,
    )
    await db.commit()
    return QueenMaintainerSettingsResponse(
        enabled=bool(row.is_active),
        feature_flag=True,
        routine_id=str(row.id),
        github_owner=settings.queen_maintainer_github_owner,
        github_repo=settings.queen_maintainer_github_repo,
        post_merge_webhook=webhook_status_payload(),
    )


@router.post("/run", summary="Trigger Queen Maintainer supervisor session now")
async def run_queen_maintainer_now(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    _ensure_admin(principal)
    if not settings.queen_maintainer_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Feature disabled.")
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    subject = f"dashboard:{principal['user'].id}"
    row = await ensure_queen_maintainer_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=subject,
        enabled=True,
    )
    result = await queue_maintainer_run(db, routine=row, trigger_source="api_manual")
    if not result.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
            if result.get("error") == "daily_limit_reached"
            else status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result,
        )
    await db.commit()
    return {
        "session_id": str(result["session_id"]),
        "routine_id": str(row.id),
        "budget": result,
    }


@router.post("/pr-draft", summary="Validate paths and prepare GitHub PR (PR-only)")
async def queen_maintainer_pr_draft(
    body: QueenMaintainerPrDraftBody,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Validate denylist and optionally create PR via github_rest connector."""

    _ensure_admin(principal)
    allowed, blocked = validate_changed_paths(body.changed_paths)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"blocked_paths": blocked, "message": "Maintainer denylist blocked one or more paths."},
        )
    branch = build_branch_name(slug=body.slug)
    result = await create_github_pr_if_configured(
        db,
        title=body.title,
        body=body.body,
        head_branch=branch,
    )
    return result


@router.post(
    "/github-webhook",
    include_in_schema=False,
    summary="GitHub post-merge webhook ingress (HMAC verified)",
)
async def queen_maintainer_github_webhook(
    request: Request,
    db: DbSession,
) -> dict[str, Any]:
    """Trigger Maintainer after PR merge or push to main/master."""

    secret = (settings.queen_maintainer_github_webhook_secret or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub webhook secret is not configured.",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256") or request.headers.get("X-Hub-Signature") or ""
    if not verify_github_webhook_signature(secret=secret, body=body, signature_header=signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub signature.")

    event = request.headers.get("X-GitHub-Event", "")
    try:
        payload = decode_github_webhook_payload(body)
        result = await handle_github_post_merge_webhook(db, event=event, payload=payload)
        await db.commit()
    except PostMergeWebhookDisabledError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PostMergeWebhookConfigError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return result
