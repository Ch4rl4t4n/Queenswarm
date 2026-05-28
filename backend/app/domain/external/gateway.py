"""REST + WebSocket gateway for Universal External Project Integration (Phase 2.5)."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.api.deps import DashboardSession, DbSession
from app.core.config import Settings, get_settings
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.domain.external.registry import (
    aggregate_metrics,
    create_external_project_row,
    emit_external_audit_trail,
    estimate_run_cost_usd,
    list_projects_for_owner,
    mint_external_api_key,
    normalize_external_slug,
    persist_run_audit,
    recent_run_series,
    resolve_external_principal,
    route_external_invocation,
)
from app.infrastructure.persistence.models.external_project import ExternalProject

logger = get_logger(__name__)

integration_router = APIRouter(tags=["External Integration"])


class ExternalProjectCreate(BaseModel):
    """Dashboard-authoritative registry intake."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(..., min_length=2, max_length=127)
    display_name: str = Field(..., min_length=2, max_length=256)
    project_kind: Literal["trading", "food_ordering", "generic"] = Field(...)
    settings: dict[str, Any] = Field(default_factory=dict)
    webhook_url: str | None = None
    webhook_secret: str | None = Field(default=None, max_length=512)


class ExternalProjectPublic(BaseModel):
    """Safe REST envelope."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    display_name: str
    project_kind: str
    settings: dict[str, Any]
    webhook_url: str | None
    is_active: bool


class ExternalApiKeyCreate(BaseModel):
    """Mint scopes alongside Postgres-backed ciphertext hashes."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=160)
    permissions: list[str] = Field(
        default_factory=lambda: ["run"],
        description='Scopes such as `run`, `mcp:call`, `trading:live`, or `"*"`.',
    )


class ExternalApiKeyMinted(BaseModel):
    """Returned exactly once."""

    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    plaintext_key: str


class ExternalRunBody(BaseModel):
    """Easy-mode REST payloads mirrored into MCP ``external_invoke``."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


def _dashboard_uuid(sess: dict[str, Any]) -> uuid.UUID:
    """Resolve UUID operators from JWT envelopes."""

    sub = sess.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard subject.")
    resolved = parse_dashboard_user_subject(sub.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard subject.")
    return resolved


async def _extract_external_credential(
    x_qs_external_key: Annotated[str | None, Header(alias="X-Queenswarm-External-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Resolve opaque ``qs_ep_`` material from headers."""

    if x_qs_external_key and x_qs_external_key.strip():
        return x_qs_external_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(None, 1)[1].strip()
        if token:
            return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Provide X-Queenswarm-External-Key or Authorization: Bearer qs_ep_…",
    )


def _payload_size_guard(payload: dict[str, Any], cfg: Settings) -> None:
    """Protect API workers from oversized JSON blobs."""

    try:
        serialized = json.dumps(payload, default=str)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="payload must serialize to JSON.",
        ) from exc
    if len(serialized) > cfg.external_integration_max_payload_chars:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Payload exceeds external_integration_max_payload_chars.",
        )


async def execute_external_invocation(
    db: AsyncSession,
    *,
    cfg: Settings,
    credential: str,
    project_slug: str,
    action: str,
    payload: dict[str, Any],
    channel: Literal["rest", "mcp", "ws"],
) -> dict[str, Any]:
    """Shared orchestration path for REST, WebSocket, and MCP transports."""

    start = time.perf_counter()
    principal = await resolve_external_principal(db, raw_key=credential)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid external API key.")

    project, api_row = principal
    slug_norm = normalize_external_slug(project_slug)
    if project.slug != slug_norm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is not scoped to this project slug.",
        )

    _payload_size_guard(payload, cfg)

    routed = await route_external_invocation(
        db,
        project=project,
        api_key=api_row,
        action=action.strip(),
        payload=payload,
        channel="mcp" if channel == "mcp" else "rest",
    )
    latency_ms = max(0, int((time.perf_counter() - start) * 1000))
    cost = estimate_run_cost_usd(action, project.project_kind)
    excerpt_cap = min(12_288, cfg.external_integration_max_payload_chars)

    audit_id = await persist_run_audit(
        db,
        project_id=project.id,
        api_key_id=api_row.id,
        action_slug=action.strip(),
        ok=routed.ok,
        latency_ms=latency_ms,
        cost_usd=cost,
        human_approval_required=routed.human_approval_required,
        human_approved=routed.human_approved,
        payload=payload,
        result_summary=routed.result,
        excerpt_cap=excerpt_cap,
    )
    await emit_external_audit_trail(
        project_slug=project.slug,
        action_slug=action.strip(),
        ok=routed.ok,
        latency_ms=latency_ms,
        audit_id=audit_id,
        summary={"channel": channel, "result": routed.result},
        api_key_id=api_row.id,
        settings=cfg,
    )
    logger.info(
        "external.run.completed",
        agent_id=str(api_row.id),
        swarm_id=project.slug,
        task_id=str(audit_id),
        channel=channel,
        ok=routed.ok,
    )
    return {
        "audit_id": str(audit_id),
        "project_slug": project.slug,
        "latency_ms": latency_ms,
        "cost_usd": float(cost),
        "ok": routed.ok,
        "result": routed.result,
    }


@integration_router.get("/projects", response_model=list[ExternalProjectPublic])
async def list_external_projects(
    db: DbSession,
    sess: DashboardSession,
) -> list[ExternalProjectPublic]:
    """Enumerate integrations owned by the signed-in dashboard operator."""

    owner = _dashboard_uuid(sess)
    rows = await list_projects_for_owner(db, owner_id=owner)
    return [ExternalProjectPublic.model_validate(r) for r in rows]


@integration_router.post(
    "/projects",
    response_model=ExternalProjectPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register_external_project(
    db: DbSession,
    sess: DashboardSession,
    body: ExternalProjectCreate,
) -> ExternalProjectPublic:
    """Create a slug-addressable integration surface."""

    owner = _dashboard_uuid(sess)
    try:
        row = await create_external_project_row(
            db,
            owner_id=owner,
            slug=body.slug,
            display_name=body.display_name,
            project_kind=body.project_kind,
            settings_blob=dict(body.settings or {}),
            webhook_url=body.webhook_url,
            webhook_plain_secret=body.webhook_secret,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug already registered.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return ExternalProjectPublic.model_validate(row)


@integration_router.post(
    "/projects/{project_id}/api-keys",
    response_model=ExternalApiKeyMinted,
    status_code=status.HTTP_201_CREATED,
)
async def create_external_project_api_key(
    db: DbSession,
    sess: DashboardSession,
    project_id: uuid.UUID,
    body: ExternalApiKeyCreate,
) -> ExternalApiKeyMinted:
    """Mint a scoped secret (shown once)."""

    owner = _dashboard_uuid(sess)
    project = await db.get(ExternalProject, project_id)
    if project is None or project.owner_dashboard_user_id != owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    key_id, plaintext = await mint_external_api_key(
        db,
        project_id=project.id,
        label=body.label,
        permissions=list(body.permissions or []),
    )
    return ExternalApiKeyMinted(id=key_id, plaintext_key=plaintext)


class ExternalMetricsResponse(BaseModel):
    """Dashboard bundle consumed by ``/external-projects``."""

    model_config = ConfigDict(from_attributes=False)

    metrics: dict[str, Any]
    series: list[dict[str, Any]]


@integration_router.get("/projects/{project_id}/metrics", response_model=ExternalMetricsResponse)
async def external_project_metrics(
    db: DbSession,
    sess: DashboardSession,
    project_id: uuid.UUID,
) -> ExternalMetricsResponse:
    """Return aggregate KPIs plus recent sparkline buckets."""

    owner = _dashboard_uuid(sess)
    project = await db.get(ExternalProject, project_id)
    if project is None or project.owner_dashboard_user_id != owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    metrics = await aggregate_metrics(db, project_id=project.id)
    series = await recent_run_series(db, project_id=project.id)
    return ExternalMetricsResponse(metrics=metrics, series=series)


@integration_router.post("/{project_slug}/run")
async def external_run_easy_mode(
    db: DbSession,
    project_slug: str,
    body: ExternalRunBody,
    cfg: Annotated[Settings, Depends(get_settings)],
    credential: Annotated[str, Depends(_extract_external_credential)],
) -> dict[str, Any]:
    """REST façade mirrored by MCP ``external_invoke``."""

    return await execute_external_invocation(
        db,
        cfg=cfg,
        credential=credential,
        project_slug=project_slug,
        action=body.action,
        payload=body.payload,
        channel="rest",
    )


@integration_router.websocket("/{project_slug}/ws")
async def external_project_ws(websocket: WebSocket, project_slug: str) -> None:
    """Bi-directional lane with heartbeat pings — authenticate via ``token`` query param."""

    cfg = get_settings()
    await websocket.accept()
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return

    from app.core.database import async_session

    try:
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=cfg.external_ws_heartbeat_sec)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping", "ts": time.time()})
                continue

            msg = json.loads(raw)
            m_type = str(msg.get("type") or "")
            if m_type == "pong":
                continue
            if m_type != "run":
                await websocket.send_json({"type": "error", "detail": "unsupported frame"})
                continue

            action = str(msg.get("action") or "").strip()
            if not action:
                await websocket.send_json({"type": "error", "detail": "action required"})
                continue
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            async with async_session() as session:
                bundle = await execute_external_invocation(
                    session,
                    cfg=cfg,
                    credential=token.strip(),
                    project_slug=project_slug,
                    action=action,
                    payload=payload,
                    channel="ws",
                )
            await websocket.send_json({"type": "result", "data": bundle})
    except WebSocketDisconnect:
        return
    except json.JSONDecodeError:
        await websocket.close(code=4400)
    except HTTPException as exc:
        detail = exc.detail
        if not isinstance(detail, str):
            detail = json.dumps(detail, default=str)
        await websocket.send_json({"type": "error", "detail": detail, "status": exc.status_code})
        await websocket.close(code=4400)


__all__ = ["execute_external_invocation", "integration_router"]
