"""Dashboard CRUD routes for Postgres-backed dynamic MCP manifests."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.presentation.api.deps import DashboardSession, DbSession
from app.infrastructure.connectors.dynamic.schemas import (
    DynamicConnectorCreateBody,
    DynamicConnectorPatchBody,
    DynamicConnectorPublic,
)
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.core.jwt_tokens import parse_dashboard_user_subject

router = APIRouter(prefix="/connectors/dynamic", tags=["Dynamic Connectors"])

__all__ = ["router"]


def _subject_uuid(sess: dict[str, Any]) -> uuid.UUID:
    raw = sess.get("sub")
    if not isinstance(raw, str) or not raw.strip():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing dashboard credential.")
    parsed = parse_dashboard_user_subject(raw.strip())
    if parsed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed subject.")
    return parsed


class DynamicConnectorListResponse(BaseModel):
    """Envelope for dashboard explorers."""

    model_config = ConfigDict(extra="ignore")

    items: list[DynamicConnectorPublic]
    builtins: list[DynamicConnectorPublic]
    customs: list[DynamicConnectorPublic]


@router.get("", summary="List built-in plus operator-defined dynamic MCP connectors")
async def list_dynamic_connectors(sess: DashboardSession, db: DbSession) -> DynamicConnectorListResponse:
    svc = DynamicConnectorService()
    uid = _subject_uuid(sess)
    items = await svc.list_visible(db, dashboard_user_id=uid)
    builtins = [row for row in items if row.is_builtin]
    customs = [row for row in items if not row.is_builtin]
    return DynamicConnectorListResponse(items=items, builtins=builtins, customs=customs)


@router.post("", summary="Create connector row (inactive until upstream test succeeds)")
async def create_dynamic_connector(sess: DashboardSession, db: DbSession, body: DynamicConnectorCreateBody) -> DynamicConnectorPublic:
    svc = DynamicConnectorService()
    uid = _subject_uuid(sess)
    try:
        return await svc.create_row(db, dashboard_user_id=uid, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/{connector_id}", summary="Patch dashboard-owned connectors")
async def patch_dynamic_connector(
    connector_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
    body: DynamicConnectorPatchBody,
) -> DynamicConnectorPublic:
    svc = DynamicConnectorService()
    uid = _subject_uuid(sess)
    try:
        return await svc.patch_row(db, connector_id=connector_id, dashboard_user_id=uid, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.delete("/{connector_id}", summary="Delete connector")
async def delete_dynamic_connector(
    connector_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
) -> Response:
    svc = DynamicConnectorService()
    uid = _subject_uuid(sess)
    try:
        await svc.delete_row(db, connector_id=connector_id, dashboard_user_id=uid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class ConnectorTestOutcome(BaseModel):
    """Smoke-test metadata without exposing secrets."""

    model_config = ConfigDict(extra="allow")

    slug: str
    ok: bool


@router.post(
    "/{connector_id}/test",
    summary="HEAD/GET base URL respecting sealed headers (activates inactive rows)",
    response_model_exclude_none=True,
)
async def post_dynamic_connector_test(
    connector_id: uuid.UUID,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    svc = DynamicConnectorService()
    uid = _subject_uuid(sess)
    try:
        return await svc.test_upstream(db, connector_id=connector_id, dashboard_user_id=uid)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
