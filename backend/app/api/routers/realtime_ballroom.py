"""Live websocket fan-out (hive pulses) and ballroom voice-lane (LLM-backed transcript)."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from sqlalchemy import func, select

from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import JwtSubject
from app.core.config import settings
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.enums import AgentStatus, TaskStatus
from app.models.task import Task

from app.services.hive_mission_runner import run_seven_step_mission

_router = APIRouter(prefix="/ws", tags=["Realtime"])
_bb_router = APIRouter(prefix="/ballroom", tags=["Ballroom"])

logger = get_logger(__name__)

_WS_IDLE_SEC: Final[float] = 6.0


class BallroomMissionBody(BaseModel):
    """POST /ballroom/mission — user brief for the fixed Orchestrator-led chain."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_brief: str = Field(..., min_length=3, max_length=30_000)
    session_id: uuid.UUID | None = None


_SESSION_CHANNELS: dict[uuid.UUID, set[WebSocket]] = {}
_CAPSULES: dict[uuid.UUID, dict[str, Any]] = {}


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


def _llm_credentials_configured() -> bool:
    """Return True when at least one LiteLLM provider key is present."""

    from app.services.llm_runtime_credentials import (
        provider_effective_anthropic,
        provider_effective_grok,
        provider_effective_openai,
    )

    grok = provider_effective_grok()
    claude = provider_effective_anthropic()
    openai = provider_effective_openai()
    return bool(grok or claude or len(openai) >= 20)


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


def _ensure_capsule(session_id: uuid.UUID) -> dict[str, Any]:
    """Allocate transcript storage for a ballroom capsule."""

    if session_id not in _CAPSULES:
        _CAPSULES[session_id] = {
            "id": str(session_id),
            "started_at": datetime.now(tz=UTC).isoformat(),
            "transcript": [],
            "participants": [],
            "status": "active",
            "discussion_scheduled": False,
        }
    return _CAPSULES[session_id]


def _append_transcript(session_id: uuid.UUID, agent: str, text: str) -> dict[str, object]:
    """Record a line and return the websocket payload."""

    cap = _ensure_capsule(session_id)
    msg: dict[str, object] = {
        "type": "ballroom.transcript",
        "agent": agent,
        "text": text,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    cap["transcript"].append(msg)
    return msg


async def _emit_placeholder_lines(session_id: uuid.UUID, lines: list[tuple[str, str]]) -> None:
    """Push deterministic dialogue when LLM is unavailable."""

    for agent, text in lines:
        await asyncio.sleep(0.65)
        payload = _append_transcript(session_id, agent, text)
        _broadcast_session_sync(session_id, payload)


async def _run_ballroom_llm_discussion(session_id: uuid.UUID) -> None:
    """Generate short multi-agent banter from recent completed tasks."""

    cap = _CAPSULES.get(session_id)
    if cap is None:
        return

    fallback: list[tuple[str, str]] = [
        ("Queen", "Ball-room is live — hook LLM keys to hear model voices."),
        ("Scout", "No completed tasks in ledger yet; run a universal bee first."),
        ("Eval", "Verification gate stands ready for the next pollen trail."),
    ]

    if not _llm_credentials_configured():
        await _emit_placeholder_lines(session_id, fallback)
        return

    try:
        async with async_session() as session:
            task_rows = list(
                (
                    await session.execute(
                        select(Task)
                        .where(Task.status == TaskStatus.COMPLETED)
                        .order_by(Task.completed_at.desc().nulls_last(), Task.created_at.desc())
                        .limit(5),
                    )
                )
                .scalars()
                .all(),
            )
            agent_rows = list(
                (
                    await session.execute(
                        select(Agent)
                        .where(Agent.status.in_((AgentStatus.IDLE, AgentStatus.RUNNING)))
                        .order_by(Agent.name)
                        .limit(6),
                    )
                )
                .scalars()
                .all(),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ballroom.context_query_failed", session_id=str(session_id), error=str(exc))
        await _emit_placeholder_lines(
            session_id,
            [("System", f"Ledger read error — placeholder hive buzz. ({type(exc).__name__})")],
        )
        return

    if not task_rows:
        await _emit_placeholder_lines(
            session_id,
            [
                (
                    "Queen",
                    "🐝 Ball-room ready — no completed tasks yet. Run agents from the hive dashboard!",
                ),
            ],
        )
        return

    task_blob = []
    for t in task_rows:
        res_preview = ""
        raw = t.result
        if isinstance(raw, dict):
            res_preview = str(raw.get("output", raw))[:220]
        task_blob.append(f"- {t.title}: {res_preview or 'no result blob'}")

    agent_names = [a.name for a in agent_rows] or ["Scout", "Eval", "Sim", "Action"]
    router = LiteLLMRouter()

    prompt = "\n".join(
        [
            f"Agents in room: {', '.join(agent_names[:5])}",
            "Recent completions:",
            *task_blob[:5],
            "",
            "Produce EXACTLY 6 dialogue lines formatted as:",
            "AGENT_NAME: short insightful line (≤100 chars, bee metaphors encouraged).",
        ],
    )

    try:
        async with async_session() as session:
            raw_text, _cost = await router.decompose(
                session,
                system_prompt=(
                    "You simulate a terse live ballroom debrief among hive agents after tasks complete. "
                    "Stay in character names provided. No Markdown fences."
                ),
                user_payload=prompt,
                swarm_id=str(session_id),
                task_id=f"ballroom-{session_id}",
            )
        lines_out: list[tuple[str, str]] = []
        for ln in raw_text.splitlines():
            chunk = ln.strip()
            if ":" not in chunk or len(chunk) < 6:
                continue
            speaker, utter = chunk.split(":", 1)
            lines_out.append((speaker.strip(), utter.strip()))

        if not lines_out:
            raise RuntimeError("model returned no NAME: utterance pairs")

        await _emit_placeholder_lines(session_id, lines_out[:8])
    except Exception as exc:  # noqa: BLE001 — ballroom must stay warm
        logger.warning("ballroom.llm_failed", session_id=str(session_id), error=str(exc))
        await _emit_placeholder_lines(
            session_id,
            fallback
            + [
                ("System", "LLM narration fell back — swarm remains operational."),
            ],
        )


def _schedule_discussion(session_id: uuid.UUID) -> None:
    """Run discussion once per capsule."""

    cap = _ensure_capsule(session_id)
    if cap.get("discussion_scheduled"):
        return
    cap["discussion_scheduled"] = True

    async def _runner() -> None:
        try:
            await _run_ballroom_llm_discussion(session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ballroom.runner_failed", session_id=str(session_id), error=str(exc))

    asyncio.create_task(_runner())


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


async def _mint_ballroom_session_capsule() -> dict[str, object]:
    """Create ballroom capsule identifiers for websocket attachment."""

    session_id = uuid.uuid4()
    _SESSION_CHANNELS.setdefault(session_id, set())
    _ensure_capsule(session_id)
    sid = str(session_id)
    return {
        "session_id": sid,
        "status": "active",
        "mode": "llm_transcript_v1",
        "ws_url": f"/api/v1/ballroom/ws/stream?session_id={sid}",
        "ws_url_path": f"/api/v1/ballroom/ws/{sid}",
        "webrtc": {"signaling": "pending_pipecat"},
    }


@_bb_router.post("/mission", status_code=status.HTTP_200_OK, summary="Seven-step Orchestrator ballroom mission")
async def ballroom_run_seven_step_mission(body: BallroomMissionBody, subject: JwtSubject) -> dict[str, object]:
    """Run Orchestrator → Managers → Workers → Managers → Orchestrator (text + voice payloads)."""

    capsule_id = body.session_id or uuid.uuid4()
    _SESSION_CHANNELS.setdefault(capsule_id, set())
    _ensure_capsule(capsule_id)
    logger.info("ballroom.mission_started", actor=subject, session_id=str(capsule_id))
    try:
        async with async_session() as session:
            payload = await run_seven_step_mission(
                session,
                user_brief=body.user_brief,
                session_id=capsule_id,
                hive_subject=subject,
            )
            await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return payload


@_bb_router.post("/session", status_code=status.HTTP_201_CREATED)
async def start_ballroom_session(_subject: JwtSubject) -> dict[str, object]:
    """Mint ballroom capsule."""

    logger.info("ballroom.session_started", actor=_subject)
    return await _mint_ballroom_session_capsule()


@_bb_router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_ballroom_session_alias(_subject: JwtSubject) -> dict[str, object]:
    """Alias ballroom start CTA."""

    logger.info("ballroom.start_via_alias", actor=_subject)
    return await _mint_ballroom_session_capsule()


@_bb_router.get("/session/{session_id}")
async def get_ballroom_session(session_id: uuid.UUID, _subject: JwtSubject) -> dict[str, object]:
    """Return transcript capsule (in-memory operator view)."""

    cap = _CAPSULES.get(session_id)
    if cap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    return dict(cap)


@_bb_router.get("/sessions")
async def list_ballroom_sessions(_subject: JwtSubject) -> dict[str, object]:
    """Lightweight ballroom registry."""

    rows = []
    for sid, cap in _CAPSULES.items():
        rows.append(
            {
                "session_id": str(sid),
                "started_at": cap.get("started_at"),
                "message_count": len(cap.get("transcript", [])),
                "status": cap.get("status"),
            },
        )
    return {"sessions": rows}


async def _ballroom_socket_loop(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str | None,
) -> None:
    """Shared consumer for ballroom websocket sessions."""

    await websocket.accept()
    subject = _decode_sub(token)
    if subject is None and settings.ballroom_guest_ws:
        subject = "ballroom-demo-guest"
    if subject is None:
        await websocket.send_json({"type": "ballroom.error", "detail": "jwt_required"})
        await websocket.close(code=1008, reason="auth")
        return

    cap = _ensure_capsule(session_id)
    sockets = _SESSION_CHANNELS.setdefault(session_id, set())
    sockets.add(websocket)

    participant = str(id(websocket))
    caps = cap.setdefault("participants", [])
    if isinstance(caps, list) and participant not in caps:
        caps.append(participant)

    hist = {"type": "history", "messages": list(cap.get("transcript", []))}
    await websocket.send_json(hist)

    ready_msg = json.dumps(
        {
            "type": "ballroom.ready",
            "session_id": str(session_id),
            "speaker": "hive-conductor",
            "text": "Ball-room channel synchronized — imitation engine narrating completions.",
        },
    )
    await websocket.send_text(ready_msg)

    _schedule_discussion(session_id)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        sockets.discard(websocket)
        plist = cap.get("participants")
        if isinstance(plist, list) and participant in plist:
            plist.remove(participant)
        if not sockets:
            _SESSION_CHANNELS.pop(session_id, None)


@_bb_router.websocket("/ws/stream")
async def ballroom_stream(
    websocket: WebSocket,
    session_id: uuid.UUID = Query(description="Capsule emitted by POST /session."),
    token: str | None = Query(default=None),
) -> None:
    """Transcript websocket (query-param session identifier)."""

    await _ballroom_socket_loop(websocket, session_id, token)


@_bb_router.websocket("/ws/{session_id}")
async def ballroom_stream_path_param(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str | None = Query(default=None),
) -> None:
    """Transcript websocket (path-param session UUID)."""

    await _ballroom_socket_loop(websocket, session_id, token)


__all__ = ["ballroom_router", "get_realtime_router"]
ballroom_router = _bb_router
