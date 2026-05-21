"""Live websocket stream for supervisor session operator audit rows."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose.exceptions import JWTError
from jose import jwt

from app.application.services.supervisor.session_audit_fanout import (
    deliver_supervisor_session_audit_local,
    register_supervisor_session_audit_local_deliver,
    supervisor_session_audit_fanout_channel,
)
from app.application.services.supervisor.session_service import get_supervisor_session
from app.core.config import settings
from app.core.database import async_session
from app.core.logging import get_logger
from app.core.redis_client import iter_pubsub_json

logger = get_logger(__name__)

router = APIRouter(tags=["supervisor-audit-live"])

_SESSION_CHANNELS: dict[uuid.UUID, set[WebSocket]] = {}
_FANOUT_TASKS: dict[uuid.UUID, asyncio.Task[None]] = {}
_WS_IDLE_SEC = 45.0


def _decode_sub(token: str | None) -> dict[str, Any] | None:
    """Decode dashboard JWT payload when passed via websocket query."""

    if not isinstance(token, str) or not token.strip():
        return None
    try:
        payload = jwt.decode(
            token.strip(),
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
    return payload if isinstance(payload, dict) else None


def _decode_sub_from_cookie_header(cookie_header: str | None) -> dict[str, Any] | None:
    """Extract dashboard JWT payload from websocket Cookie header."""

    if not cookie_header:
        return None
    for chunk in cookie_header.split(";"):
        part = chunk.strip()
        if not part.startswith("qs_dashboard_at="):
            continue
        return _decode_sub(part.split("=", 1)[1].strip())
    return None


def _decode_ws_claims(websocket: WebSocket, token: str | None) -> dict[str, Any] | None:
    """Resolve dashboard JWT claims via query token, auth header, or cookie."""

    claims = _decode_sub(token)
    if claims is not None:
        return claims
    auth_header = websocket.headers.get("authorization")
    if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        claims = _decode_sub(auth_header[7:].strip())
        if claims is not None:
            return claims
    return _decode_sub_from_cookie_header(websocket.headers.get("cookie"))


def _tenant_id_from_claims(claims: dict[str, Any]) -> uuid.UUID | None:
    raw = claims.get("tenant_id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return uuid.UUID(raw.strip())
    except ValueError:
        return None


async def _deliver_supervisor_session_audit_local(
    session_id: uuid.UUID,
    payload: dict[str, Any],
) -> None:
    """Push JSON payload to audit-live sockets attached on this worker."""

    sockets = _SESSION_CHANNELS.get(session_id)
    if not sockets:
        return
    stale: list[WebSocket] = []
    for chan in list(sockets):
        try:
            await chan.send_json(payload)
        except Exception:
            stale.append(chan)
    for dead in stale:
        sockets.discard(dead)


async def _fanout_worker_loop(session_id: uuid.UUID) -> None:
    """Subscribe for cross-worker audit Pub/Sub."""

    try:
        channel = supervisor_session_audit_fanout_channel(session_id)
        async for envelope in iter_pubsub_json(channel):
            await _deliver_supervisor_session_audit_local(session_id, envelope)
    except asyncio.CancelledError:
        raise


def _maybe_start_fanout_worker(session_id: uuid.UUID) -> None:
    """Ensure one Redis listener task runs per session."""

    probe = _FANOUT_TASKS.get(session_id)
    if probe is not None and not probe.done():
        return
    _FANOUT_TASKS[session_id] = asyncio.create_task(
        _fanout_worker_loop(session_id),
        name=f"qs-supervisor-audit-fanout-{session_id}",
    )


def _cancel_fanout_worker(session_id: uuid.UUID) -> None:
    """Stop Redis listener when the last socket disconnects."""

    if _SESSION_CHANNELS.get(session_id):
        return
    task = _FANOUT_TASKS.pop(session_id, None)
    if task is not None:
        task.cancel()


register_supervisor_session_audit_local_deliver(_deliver_supervisor_session_audit_local)


@router.websocket("/sessions/{session_id}/audit-live")
async def supervisor_session_audit_live(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str | None = Query(default=None),
) -> None:
    """Stream operator audit rows for one supervisor session in near real time."""

    await websocket.accept()
    claims = _decode_ws_claims(websocket, token)
    tenant_id = _tenant_id_from_claims(claims or {})
    if tenant_id is None:
        await websocket.send_json({"type": "supervisor_session.audit.error", "detail": "tenant_context_required"})
        await websocket.close(code=1008, reason="auth")
        return

    async with async_session() as db:
        row = await get_supervisor_session(db, session_id)
        if row is None or row.tenant_id != tenant_id:
            await websocket.send_json({"type": "supervisor_session.audit.error", "detail": "session_not_found"})
            await websocket.close(code=1008, reason="forbidden")
            return

    sockets = _SESSION_CHANNELS.setdefault(session_id, set())
    sockets.add(websocket)
    _maybe_start_fanout_worker(session_id)
    await websocket.send_json({"type": "supervisor_session.audit.ready", "session_id": str(session_id)})

    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=_WS_IDLE_SEC)
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        logger.debug("supervisor_session_audit.ws_disconnect", session_id=str(session_id))
    finally:
        sockets.discard(websocket)
        if not sockets:
            _SESSION_CHANNELS.pop(session_id, None)
        _cancel_fanout_worker(session_id)


__all__ = ["router"]
