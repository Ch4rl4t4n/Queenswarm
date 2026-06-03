"""Publish Queue — Phase B operator approval inbox."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.publish_queue import (
    PublishQueueBulkReviewBody,
    PublishQueueBulkReviewResultOut,
    PublishQueueReviewBody,
    PublishQueueReviewResultOut,
    PublishQueueSnapshotOut,
    build_publish_queue_snapshot,
    bulk_review_publish_queue,
    review_publish_queue_item,
)
from app.application.services.publish_queue_notify import _resolve_tenant_for_user
from app.application.services.publish_queue_policy import (
    merge_publish_queue_policy_patch,
    publish_queue_policy,
)
from app.core.config import settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DashboardSession, DbSession

router = APIRouter(prefix="/publish-queue", tags=["Publish Queue"])


def _dashboard_principal(session_payload: DashboardSession) -> uuid.UUID:
    raw = session_payload.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing dashboard subject.")
    resolved = parse_dashboard_user_subject(raw.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard subject.")
    return resolved


def _require_enabled() -> None:
    if not settings.publish_queue_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publish queue disabled.")


class PublishQueuePolicyView(BaseModel):
    """Tenant publish queue approval policy."""

    auto_approve_enabled: bool


class PublishQueuePolicyPatch(BaseModel):
    """Partial patch for publish queue approval policy."""

    model_config = ConfigDict(extra="forbid")

    auto_approve_enabled: bool | None = None


async def _tenant_for_dashboard_user(db: DbSession, *, dashboard_user_id: uuid.UUID) -> Tenant | None:
    return await _resolve_tenant_for_user(db, dashboard_user_id=dashboard_user_id)


@router.get("/policy", response_model=PublishQueuePolicyView, summary="Read publish queue approval policy")
async def get_publish_queue_policy(
    db: DbSession,
    sess: DashboardSession,
) -> PublishQueuePolicyView:
    """Return tenant publish queue auto-approve policy."""

    _require_enabled()
    user_id = _dashboard_principal(sess)
    tenant = await _tenant_for_dashboard_user(db, dashboard_user_id=user_id)
    policy = publish_queue_policy(tenant)
    return PublishQueuePolicyView(auto_approve_enabled=bool(policy["auto_approve_enabled"]))


@router.patch("/policy", response_model=PublishQueuePolicyView, summary="Update publish queue approval policy")
async def patch_publish_queue_policy(
    body: PublishQueuePolicyPatch,
    db: DbSession,
    sess: DashboardSession,
) -> PublishQueuePolicyView:
    """Persist publish queue auto-approve policy and optionally drain pending packs."""

    _require_enabled()
    user_id = _dashboard_principal(sess)
    tenant = await _tenant_for_dashboard_user(db, dashboard_user_id=user_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    patch_data = body.model_dump(exclude_unset=True)
    tenant.operator_settings = merge_publish_queue_policy_patch(tenant.operator_settings, patch_data)
    await db.flush()
    policy = publish_queue_policy(tenant)
    if patch_data.get("auto_approve_enabled") is True:
        from app.application.services.publish_queue_auto_approve import auto_approve_pending_publish_queue

        reviewed_by = str(sess.get("sub") or "")
        await auto_approve_pending_publish_queue(
            db,
            dashboard_user_id=user_id,
            reviewed_by=reviewed_by,
        )
    await db.commit()
    await db.refresh(tenant)
    policy = publish_queue_policy(tenant)
    return PublishQueuePolicyView(auto_approve_enabled=bool(policy["auto_approve_enabled"]))


@router.get("", response_model=PublishQueueSnapshotOut, summary="Publish queue snapshot")
async def get_publish_queue_snapshot(
    db: DbSession,
    sess: DashboardSession,
) -> PublishQueueSnapshotOut:
    """Single snapshot for lazy Publish Queue panel — pending + recent decisions."""

    _require_enabled()
    user_id = _dashboard_principal(sess)
    reviewed_by = str(sess.get("sub") or "")
    tenant = await _tenant_for_dashboard_user(db, dashboard_user_id=user_id)
    policy = publish_queue_policy(tenant)
    from app.application.services.publish_queue_auto_approve import maybe_auto_approve_publish_queue_pending

    drained = await maybe_auto_approve_publish_queue_pending(
        db,
        tenant=tenant,
        dashboard_user_id=user_id,
        reviewed_by=reviewed_by,
    )
    if int(drained.get("processed", 0)) > 0:
        await db.commit()
    snapshot = await build_publish_queue_snapshot(
        db,
        dashboard_user_id=user_id,
        auto_approve_enabled=bool(policy["auto_approve_enabled"]),
    )
    snapshot.enabled = True
    return snapshot


@router.post(
    "/{deliverable_id}/review",
    response_model=PublishQueueReviewResultOut,
    summary="Approve or reject one publish pack",
)
async def review_publish_queue_deliverable(
    deliverable_id: uuid.UUID,
    body: PublishQueueReviewBody,
    db: DbSession,
    sess: DashboardSession,
) -> PublishQueueReviewResultOut:
    """Operator approval — simulate-only; live Instagram is Phase C."""

    _require_enabled()
    user_id = _dashboard_principal(sess)
    reviewed_by = str(sess.get("sub") or "")
    try:
        result = await review_publish_queue_item(
            db,
            deliverable_id=deliverable_id,
            dashboard_user_id=user_id,
            decision=body.decision,
            note=body.note,
            reviewed_by=reviewed_by,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await db.commit()
    return result


@router.post(
    "/bulk-review",
    response_model=PublishQueueBulkReviewResultOut,
    summary="Batch approve or reject publish packs",
)
async def bulk_review_publish_queue_deliverables(
    body: PublishQueueBulkReviewBody,
    db: DbSession,
    sess: DashboardSession,
) -> PublishQueueBulkReviewResultOut:
    """Morning workflow — approve selected packs in one request."""

    _require_enabled()
    user_id = _dashboard_principal(sess)
    reviewed_by = str(sess.get("sub") or "")
    result = await bulk_review_publish_queue(
        db,
        deliverable_ids=body.deliverable_ids,
        dashboard_user_id=user_id,
        decision=body.decision,
        note=body.note,
        reviewed_by=reviewed_by,
    )
    await db.commit()
    return result


__all__ = ["router"]
