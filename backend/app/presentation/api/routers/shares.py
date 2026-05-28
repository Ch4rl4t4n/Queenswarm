"""Public sharing endpoints for outputs, sessions, and swarms."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.infrastructure.persistence.models.public_share import PublicShareLink
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.core.tenant_context import set_current_tenant_id
from app.application.services.tenancy import write_tenant_audit_log
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role, require_tenant_permission
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit

ResourceType = Literal["output", "session", "swarm"]
_ALLOWED_RESOURCE_TYPES: set[str] = {"output", "session", "swarm"}

router = APIRouter(prefix="/shares", tags=["Shares"])
public_router = APIRouter(prefix="/public/share", tags=["Public"])


class ShareCreateBody(BaseModel):
    """Create one public share link."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    resource_type: ResourceType
    resource_id: uuid.UUID
    expires_in_days: int | None = Field(default=30, ge=1, le=365)


class ShareView(BaseModel):
    """Share row view for settings UI."""

    id: str
    resource_type: str
    resource_id: str
    share_token: str
    is_active: bool
    access_count: int
    expires_at: str | None
    created_at: str
    public_url: str


class PublicSharePayload(BaseModel):
    """Read-only payload envelope for unauthenticated viewers."""

    resource_type: str
    resource: dict[str, Any]
    shared_at: str
    expires_at: str | None = None


def _public_url(token: str) -> str:
    return f"/api/v1/public/share/{token}"


async def _validate_share_target(
    *,
    db: DbSession,
    tenant_id: uuid.UUID,
    principal_user_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
) -> None:
    if resource_type == "output":
        row = await db.get(TaskFinalDeliverable, resource_id)
        if row is None or row.dashboard_user_id != principal_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Output not found.")
        return
    if resource_type == "session":
        row = await db.get(SupervisorSession, resource_id)
        if row is None or row.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return
    if resource_type == "swarm":
        row = await db.get(SubSwarm, resource_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm not found.")
        scoped_task_count = int(
            await db.scalar(
                select(func.count()).select_from(Task).where(
                    Task.swarm_id == resource_id,
                    Task.tenant_id == tenant_id,
                ),
            )
            or 0,
        )
        if scoped_task_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swarm not scoped to tenant.")
        return
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported resource type.")


def _serialize_share(row: PublicShareLink) -> ShareView:
    return ShareView(
        id=str(row.id),
        resource_type=row.resource_type,
        resource_id=str(row.resource_id),
        share_token=row.share_token,
        is_active=bool(row.is_active),
        access_count=int(row.access_count or 0),
        expires_at=row.expires_at.isoformat() if row.expires_at else None,
        created_at=row.created_at.isoformat(),
        public_url=_public_url(row.share_token),
    )


@router.get("", response_model=list[ShareView], summary="List tenant share links")
async def list_share_links(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("resources:share")),
) -> list[ShareView]:
    tenant_id = principal["tenant_id"]
    rows = list(
        (
            await db.scalars(
                select(PublicShareLink)
                .where(PublicShareLink.tenant_id == tenant_id)
                .order_by(PublicShareLink.created_at.desc()),
            )
        ).all(),
    )
    return [_serialize_share(row) for row in rows]


@router.post("", response_model=ShareView, status_code=status.HTTP_201_CREATED, summary="Create public share link")
async def create_share_link(
    body: ShareCreateBody,
    db: DbSession,
    request: Request,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("resources:share")),
) -> ShareView:
    tenant_id = principal["tenant_id"]
    user_id = principal["user"].id
    if body.resource_type not in _ALLOWED_RESOURCE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported resource type.")
    await _validate_share_target(
        db=db,
        tenant_id=tenant_id,
        principal_user_id=user_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
    )
    expires_at = (
        datetime.now(tz=UTC) + timedelta(days=int(body.expires_in_days))
        if body.expires_in_days is not None
        else None
    )
    token = secrets.token_urlsafe(28)
    row = PublicShareLink(
        tenant_id=tenant_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        share_token=token,
        created_by_user_id=user_id,
        is_active=True,
        expires_at=expires_at,
        access_count=0,
    )
    db.add(row)
    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=user_id,
        action="share_created",
        target_type=body.resource_type,
        target_ref=str(body.resource_id),
        payload={"share_id": str(row.id)},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    await db.refresh(row)
    return _serialize_share(row)


@router.delete(
    "/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revoke share link",
)
async def revoke_share_link(
    share_id: uuid.UUID,
    db: DbSession,
    request: Request,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _: bool = Depends(require_tenant_permission("resources:share")),
) -> Response:
    tenant_id = principal["tenant_id"]
    row = await db.get(PublicShareLink, share_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found.")
    row.is_active = False
    await write_tenant_audit_log(
        db,
        tenant_id=tenant_id,
        actor_user_id=principal["user"].id,
        action="share_revoked",
        target_type=row.resource_type,
        target_ref=str(row.resource_id),
        payload={"share_id": str(row.id)},
        client_ip=peer_ip_for_rate_limit(request),
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@public_router.get("/{share_token}", response_model=PublicSharePayload, summary="Resolve public share payload")
async def get_public_share_payload(share_token: str, db: DbSession) -> PublicSharePayload:
    set_current_tenant_id(None)
    row = await db.scalar(select(PublicShareLink).where(PublicShareLink.share_token == share_token.strip()))
    if row is None or not row.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found.")
    now = datetime.now(tz=UTC)
    if row.expires_at is not None:
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if exp < now:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired.")

    payload: dict[str, Any]
    if row.resource_type == "output":
        doc = await db.get(TaskFinalDeliverable, row.resource_id)
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared output missing.")
        payload = {
            "id": str(doc.id),
            "title": doc.title,
            "slug": doc.slug,
            "version": int(doc.version),
            "created_at": doc.created_at.isoformat(),
            "markdown_body": doc.markdown_body,
            "tags": list(doc.tags or []),
        }
    elif row.resource_type == "session":
        sess = await db.get(SupervisorSession, row.resource_id)
        if sess is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared session missing.")
        payload = {
            "id": str(sess.id),
            "goal": sess.goal,
            "status": sess.status,
            "runtime_mode": sess.runtime_mode,
            "created_at": sess.created_at.isoformat(),
            "completed_at": sess.completed_at.isoformat() if sess.completed_at else None,
            "context_summary": dict(sess.context_summary or {}),
        }
    elif row.resource_type == "swarm":
        swarm = await db.get(SubSwarm, row.resource_id)
        if swarm is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared swarm missing.")
        payload = {
            "id": str(swarm.id),
            "name": swarm.name,
            "purpose": getattr(swarm.purpose, "value", str(swarm.purpose)),
            "member_count": int(swarm.member_count),
            "total_pollen": float(swarm.total_pollen),
            "is_active": bool(swarm.is_active),
            "last_global_sync_at": swarm.last_global_sync_at.isoformat() if swarm.last_global_sync_at else None,
            "local_memory": dict(swarm.local_memory or {}),
        }
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unsupported share type.")

    row.access_count = int(row.access_count or 0) + 1
    await db.commit()
    return PublicSharePayload(
        resource_type=row.resource_type,
        resource=payload,
        shared_at=row.created_at.isoformat(),
        expires_at=row.expires_at.isoformat() if row.expires_at else None,
    )


__all__ = ["router", "public_router"]
