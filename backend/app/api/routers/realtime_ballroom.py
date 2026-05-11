"""Live websocket fan-out (hive pulses) and ballroom stubs (voice lane)."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Final

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import func, select

from app.api.deps import JwtSubject
from app.core.config import settings
from app.core.database import async_session
from app.models.agent import Agent
from app.models.enums import TaskStatus
from app.models.task import Task

_router = APIRouter(prefix="/ws", tags=["Realtime"])
_bb_router = APIRouter(prefix="/ballroom", tags=["Ballroom"])

_WS_IDLE_SEC: Final[float] = 6.0

_SESSION_CHANNELS: dict[uuid.UUID, set[WebSocket]] = {}


def _decode_sub(token: str | None) -> str | None:
    """Decode JWT ``sub`` when browsers pass Bearer via websocket query."""

    if not isinstance(token, str) or token.strip() == "":
        return None
    try:
        payload = jwt.decode(
            token.strip(),
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub.strip() else None


async def _build_pulse_payload() -> dict[str, object]:
    """Hydrate counters for realtime badges."""

    async with async_session() as session:
        agent_ct = await session.scalar(select(func.count()).select_from(Agent))
        pending = await session.scalar(
            select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING),
        )
        pollen = await session.scalar(select(func.coalesce(func.sum(Agent.pollen_points), 0.0)))
    return {
        "type": "hive.snapshot",
        "agents": int(agent_ct or 0),
        "tasks_pending": int(pending or 0),
        "pollen_points_total": float(pollen or 0.0),
    }


def _broadcast_session_sync(session_id: uuid.UUID, message: dict[str, object]) -> None:
    """Schedule JSON broadcast tasks for each ballroom websocket."""

    sockets = _SESSION_CHANNELS.get(session_id)
    if not sockets:
        return

    async def _emit_all() -> None:
        stale: list[WebSocket] = []
        copy = list(sockets)
        for chan in copy:
            try:
                await chan.send_json(message)
            except Exception:
                stale.append(chan)
        for dead in stale:
            sockets.discard(dead)

    asyncio.create_task(_emit_all())


@_router.websocket("/live")
async def hive_live_channel(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    """Hive dashboard stream emitting periodic swarm snapshots."""

    await websocket.accept()
    subject = _decode_sub(token)
    if subject is None and settings.hive_dashboard_guest_ws:
        subject = "hive-dashboard-guest"
    if subject is None:
        await websocket.send_json({"type": "hive.error", "detail": "valid_jwt_via_query_required"})
        await websocket.close(code=1008, reason="auth")
        return

    try:
        while True:
            payload = await asyncio.wait_for(
                _build_pulse_payload(),
                timeout=float(settings.rapid_loop_timeout_sec),
            )
            await websocket.send_json(payload)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=_WS_IDLE_SEC)
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        return


def get_realtime_router() -> APIRouter:
    """Expose realtime routes for orchestration mounts."""

    return _router


@_bb_router.post("/session", status_code=status.HTTP_201_CREATED)
async def start_ballroom_session(_subject: JwtSubject) -> dict[str, object]:
    """Mint a ballroom capsule (stub until Pipecat + WebRTC infra keys are wired)."""

    session_id = uuid.uuid4()
    _SESSION_CHANNELS.setdefault(session_id, set())
    return {
        "session_id": str(session_id),
        "mode": "pipecat_stub",
        "transcript_query": "?session_id=...&token=...",
        "webrtc": {"signaling": "mock"},
    }


@_bb_router.websocket("/ws/stream")
async def ballroom_stream(
    websocket: WebSocket,
    session_id: uuid.UUID = Query(description="Capsule emitted by POST /session."),
    token: str | None = Query(default=None),
) -> None:
    """Transcript websocket that simulates ballroom banter."""

    await websocket.accept()
    subject = _decode_sub(token)
    if subject is None and settings.ballroom_guest_ws:
        subject = "ballroom-demo-guest"
    if subject is None:
        await websocket.send_json({"type": "ballroom.error", "detail": "jwt_required"})
        await websocket.close(code=1008, reason="auth")
        return

    sockets = _SESSION_CHANNELS.setdefault(session_id, set())
    sockets.add(websocket)

    greeting = json.dumps(
        {
            "type": "ballroom.ready",
            "session_id": str(session_id),
            "speaker": "hive-conductor-stub",
            "text": "Ballroom channel open — imitation engine standing by.",
        },
    )
    await websocket.send_text(greeting)

    mock_lines = (
        ("evaluator-scout", "Verified sentiment probe neutral."),
        ("simulator-worker", "Docker sandbox GREEN — gate cleared."),
        ("learner-agent", "Recipe match 0.86 — pollen reward escalating."),
    )
    seq = {"i": 0}

    async def pump() -> None:
        while True:
            await asyncio.sleep(4.5)
            idx = seq["i"] % len(mock_lines)
            seq["i"] += 1
            speaker, utterance = mock_lines[idx]
            _broadcast_session_sync(
                session_id,
                {"type": "ballroom.transcript", "agent": speaker, "text": utterance},
            )

    ticker = asyncio.create_task(pump())
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ticker.cancel()
        sockets.discard(websocket)
        if not sockets:
            _SESSION_CHANNELS.pop(session_id, None)


__all__ = ["ballroom_router", "get_realtime_router"]
ballroom_router = _bb_router
