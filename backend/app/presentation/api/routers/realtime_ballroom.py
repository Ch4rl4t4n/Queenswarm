"""Live websocket fan-out (hive pulses) and ballroom voice-lane (LLM-backed transcript)."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Final, Literal

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.presentation.api.deps import JwtSubject
from app.core.config import settings
from app.core.database import async_session
from app.core.llm_router import LiteLLMRouter
from app.core.logging import get_logger
from app.application.services.xai_voice_live import XaiVoiceLiveError, mint_voice_live_client_secret
from app.application.services.ballroom_fast_llm import grok_ballroom_reply_fast
from app.application.services.llm_runtime_credentials import provider_effective_grok
from app.application.services.voice_exceptions import VoiceEmptyTranscriptionError, VoiceServiceError
from app.application.services.voice_multimodal import (
    synthesize_speech,
    transcribe_audio,
)
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentStatus, TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.application.services import ballroom_store as ballroom_redis
from app.application.services.hive_mission_runner import run_seven_step_mission

_router = APIRouter(prefix="/ws", tags=["Realtime"])
_bb_router = APIRouter(prefix="/ballroom", tags=["Ballroom"])

logger = get_logger(__name__)

_WS_IDLE_SEC: Final[float] = 6.0

_SESSION_CHANNELS: dict[uuid.UUID, set[WebSocket]] = {}
_FANOUT_TASKS: dict[uuid.UUID, asyncio.Task[Any]] = {}


class BallroomMissionBody(BaseModel):
    """POST /ballroom/mission — user brief for the fixed Orchestrator-led chain."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_brief: str = Field(..., min_length=3, max_length=30_000)
    session_id: uuid.UUID | None = None


class BallroomChatMessageBody(BaseModel):
    """POST /ballroom/message — inbound operator text for multi-agent Ballroom replies."""

    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: uuid.UUID
    text: str = Field(..., min_length=1, max_length=30_000)
    mode: Literal["swarm", "orchestrator"] = "swarm"
    preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto"
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto"
    latency_mode: Literal["balanced", "fast"] = "balanced"
    tts_voice_id: str | None = Field(default=None, max_length=64)
    tts_language: str | None = Field(default=None, max_length=16)
    tts_tone: str | None = Field(default=None, max_length=32)


class BallroomVoiceTranscribeBody(BaseModel):
    """POST /ballroom/voice/transcribe — STT chunk for live transcription."""

    model_config = ConfigDict(str_strip_whitespace=True)

    audio_base64: str = Field(..., min_length=20, max_length=8_000_000)
    mime_type: str = Field(default="audio/webm", min_length=6, max_length=64)
    language: str | None = Field(default="auto", max_length=12)
    session_id: uuid.UUID | None = None
    dispatch_to_agents: bool = False
    target_mode: Literal["swarm", "orchestrator"] = "swarm"
    preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto"
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto"
    latency_mode: Literal["balanced", "fast"] = "balanced"
    tts_voice_id: str | None = Field(default=None, max_length=64)
    tts_language: str | None = Field(default=None, max_length=16)
    tts_tone: str | None = Field(default=None, max_length=32)


class BallroomVoiceSynthesizeBody(BaseModel):
    """POST /ballroom/voice/synthesize — TTS for operator playback."""

    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(..., min_length=1, max_length=6_000)
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto"
    latency_mode: Literal["balanced", "fast"] = "balanced"
    tts_voice_id: str | None = Field(default=None, max_length=64)
    tts_language: str | None = Field(default=None, max_length=16)
    tts_tone: str | None = Field(default=None, max_length=32)


class BallroomVoiceCapabilitiesResponse(BaseModel):
    """Runtime voice capability report used by Ballroom frontend."""

    ok: bool
    voice_enabled: bool
    stt_enabled: bool
    tts_enabled: bool
    stt_provider: str | None = None
    tts_provider: str | None = None
    detail: str | None = None


class BallroomSessionMetaBody(BaseModel):
    """PATCH /ballroom/session/{id}/meta — lightweight session metadata edits."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, max_length=80)
    pinned: bool | None = None


class BallroomChatPromptBody(BaseModel):
    """POST /ballroom/session/{id}/prompt — operator assignment brief for Orchestrator."""

    model_config = ConfigDict(str_strip_whitespace=True)

    label: str = Field(..., min_length=1, max_length=40)
    text: str = Field(..., min_length=1, max_length=4_000)


_ORCH_BASE_SYSTEM: Final[str] = (
    "You are the Queenswarm Orchestrator in live voice chat. "
    "Provide crisp actionable guidance with no markdown."
)


def _read_capsule_chat_prompt(cap: dict[str, Any]) -> dict[str, str] | None:
    """Return active session assignment brief from capsule, if any."""

    raw = cap.get("chat_prompt")
    if not isinstance(raw, dict):
        return None
    label = str(raw.get("label") or "").strip()
    text = str(raw.get("text") or "").strip()
    if not text:
        return None
    return {"label": label or "Assignment", "text": text}


def _orchestrator_system_prompt(chat_prompt: dict[str, str] | None, *, voice: bool = False) -> str:
    """Build Orchestrator system prompt with optional session assignment brief."""

    if voice:
        base = (
            "You are the Queenswarm Orchestrator. Have a natural spoken conversation with the operator. "
            "Be concise, helpful, and direct. No markdown. Respond in the same language the user speaks."
        )
    else:
        base = _ORCH_BASE_SYSTEM
    if not chat_prompt:
        return base
    return (
        f"{base}\n\n"
        f"## Active session assignment ({chat_prompt['label']})\n"
        f"Follow this brief for every reply until the operator changes it:\n"
        f"{chat_prompt['text']}"
    )


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


def _resolve_stt_language(*, language: str | None, tts_language: str | None) -> str | None:
    """Pick STT language from chunk hint or voice preference (auto = provider detect)."""

    for candidate in (language, tts_language):
        raw = (candidate or "").strip().lower()
        if not raw or raw == "auto":
            continue
        return candidate.strip() if candidate else None
    return None


def _decode_sub_from_cookie_header(cookie_header: str | None) -> str | None:
    """Extract dashboard access token from websocket Cookie header."""

    if not cookie_header:
        return None
    parts = [chunk.strip() for chunk in cookie_header.split(";") if chunk.strip()]
    for chunk in parts:
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        if key.strip() != "qs_dashboard_at":
            continue
        return _decode_sub(value.strip())
    return None


def _decode_ws_subject(websocket: WebSocket, token: str | None) -> str | None:
    """Resolve websocket subject via query token, auth header, or dashboard cookie."""

    subject = _decode_sub(token)
    if subject is not None:
        return subject
    auth_header = websocket.headers.get("authorization")
    if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        subject = _decode_sub(auth_header[7:].strip())
        if subject is not None:
            return subject
    return _decode_sub_from_cookie_header(websocket.headers.get("cookie"))


def _voice_capabilities() -> BallroomVoiceCapabilitiesResponse:
    """Compute current server-side STT/TTS availability."""

    from app.application.services.llm_runtime_credentials import provider_effective_openai
    from app.application.services.llm_runtime_credentials import (
        provider_effective_deepgram,
        provider_effective_elevenlabs,
        provider_effective_grok,
    )

    openai_key = provider_effective_openai().strip()
    deepgram_key = provider_effective_deepgram().strip()
    eleven_key = provider_effective_elevenlabs().strip()
    grok_key = provider_effective_grok().strip()

    voice_enabled = bool(settings.voice_enabled)
    stt_enabled = bool(voice_enabled and (grok_key or deepgram_key or openai_key))
    tts_enabled = bool(voice_enabled and (grok_key or eleven_key or openai_key))
    stt_provider = (
        "grok_stt"
        if (voice_enabled and grok_key)
        else ("deepgram" if (voice_enabled and deepgram_key) else ("openai_whisper" if stt_enabled else None))
    )
    tts_provider = (
        "grok_tts"
        if (voice_enabled and grok_key)
        else ("elevenlabs" if (voice_enabled and eleven_key) else ("openai_tts" if tts_enabled else None))
    )

    detail: str | None = None
    if not voice_enabled:
        detail = "VOICE_ENABLED is false on backend."
    elif not stt_enabled:
        detail = "STT unavailable: missing Grok/Deepgram/OpenAI API key."
    elif not tts_enabled:
        detail = "TTS unavailable: missing Grok/ElevenLabs/OpenAI API key."

    return BallroomVoiceCapabilitiesResponse(
        ok=bool(stt_enabled and tts_enabled),
        voice_enabled=voice_enabled,
        stt_enabled=stt_enabled,
        tts_enabled=tts_enabled,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        detail=detail,
    )


def _llm_credentials_configured() -> bool:
    """Return True when at least one LiteLLM provider key is present."""

    from app.application.services.llm_runtime_credentials import (
        provider_effective_anthropic,
        provider_effective_grok,
        provider_effective_openai,
    )

    grok = provider_effective_grok()
    claude = provider_effective_anthropic()
    openai = provider_effective_openai()
    return bool(grok or claude or len(openai) >= 20)


async def _deliver_ballroom_ws_local(session_id: uuid.UUID, payload: dict[str, Any]) -> None:
    """Push JSON payload to sockets attached on this worker."""

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
    """Subscribe for cross-worker Ballroom Pub/Sub (Redis backend only)."""

    try:
        async for envelope in ballroom_redis.ballroom_iter_fanout_messages(session_id):
            await _deliver_ballroom_ws_local(session_id, envelope)
    except asyncio.CancelledError:
        raise


def _maybe_start_fanout_worker(session_id: uuid.UUID) -> None:
    """Ensure a single listener task runs per Ballroom session."""

    if settings.ballroom_capsule_backend == "memory":
        return
    probe = _FANOUT_TASKS.get(session_id)
    if probe is not None and not probe.done():
        return
    _FANOUT_TASKS[session_id] = asyncio.create_task(
        _fanout_worker_loop(session_id),
        name=f"qs-ballroom-fanout-{session_id}",
    )


def _cancel_fanout_worker(session_id: uuid.UUID) -> None:
    task = _FANOUT_TASKS.pop(session_id, None)
    if task is not None:
        task.cancel()


async def ballroom_dispatch_fanout(session_id: uuid.UUID, payload: dict[str, Any]) -> None:
    """Deliver ballroom payload locally (tests) or via Redis Pub/Sub + subscriber loop."""

    if settings.ballroom_capsule_backend == "memory":
        await _deliver_ballroom_ws_local(session_id, payload)
        return

    _maybe_start_fanout_worker(session_id)
    await ballroom_redis.ballroom_publish_fanout(session_id, payload)


async def append_ballroom_transcript_line_public(
    session_id: uuid.UUID,
    agent: str,
    text: str,
    *,
    broadcast: bool = True,
) -> dict[str, object] | None:
    """Append a Ballroom transcript chunk and optionally fan-out (mission runner API)."""

    cap = await ballroom_redis.ballroom_ensure_capsule(session_id)
    msg: dict[str, Any] = {
        "type": "ballroom.transcript",
        "agent": agent,
        "text": text,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    hist = cap.setdefault("transcript", [])
    hist.append(msg)
    await ballroom_redis.ballroom_save_capsule(session_id, cap)
    if broadcast:
        await ballroom_dispatch_fanout(session_id, msg)
    return msg if broadcast else None


async def append_ballroom_orchestrator_out_public(session_id: uuid.UUID, orchestrator_payload: dict[str, Any]) -> None:
    """Persist orchestrator stream rows for mission-seven summaries."""

    cap = await ballroom_redis.ballroom_ensure_capsule(session_id)
    hist = cap.setdefault("transcript", [])
    hist.append(orchestrator_payload)
    await ballroom_redis.ballroom_save_capsule(session_id, cap)
    await ballroom_dispatch_fanout(session_id, orchestrator_payload)


async def append_silent_chat_line_public(session_id: uuid.UUID, agent: str, text: str) -> None:
    """Append operator text without websocket fan-out."""

    cap = await ballroom_redis.ballroom_ensure_capsule(session_id)
    msg: dict[str, Any] = {
        "type": "ballroom.transcript",
        "agent": agent,
        "text": text,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    cap.setdefault("transcript", []).append(msg)
    await ballroom_redis.ballroom_save_capsule(session_id, cap)


async def _build_pulse_payload() -> dict[str, object]:
    """Hydrate counters and agent deltas for realtime badges."""

    async with async_session() as session:
        from app.application.services.hive_live_pulse import build_hive_live_pulse_payload

        return await build_hive_live_pulse_payload(session)


async def _emit_placeholder_lines(session_id: uuid.UUID, lines: list[tuple[str, str]]) -> None:
    """Push deterministic dialogue when LLM is unavailable."""

    for agent, text in lines:
        await asyncio.sleep(0.65)
        payload = await append_ballroom_transcript_line_public(session_id, agent, text, broadcast=True)
        if payload is None:
            continue


async def _run_ballroom_llm_discussion(session_id: uuid.UUID) -> None:
    """Generate short multi-agent banter from recent completed tasks."""

    if not await ballroom_redis.ballroom_has_capsule(session_id):
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
            fallback + [("System", "LLM narration fell back — swarm remains operational.")],
        )


def _schedule_discussion(session_id: uuid.UUID) -> None:
    """Run discussion once per capsule."""

    async def _runner_prep() -> None:
        cap = await ballroom_redis.ballroom_ensure_capsule(session_id)
        if cap.get("discussion_scheduled"):
            return
        cap["discussion_scheduled"] = True
        await ballroom_redis.ballroom_save_capsule(session_id, cap)
        try:
            await _run_ballroom_llm_discussion(session_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ballroom.runner_failed", session_id=str(session_id), error=str(exc))

    asyncio.create_task(_runner_prep())


def _fallback_chat_lines(agent_names: list[str], user_text: str) -> list[tuple[str, str]]:
    """Short canned replies tied to persisted agent names."""

    clipped = user_text.strip()
    preview = clipped if len(clipped) <= 120 else f"{clipped[:117]}..."
    orch = agent_names[0] if agent_names else "Orchestrator"
    second = agent_names[1] if len(agent_names) > 1 else "Scout"
    third = agent_names[2] if len(agent_names) > 2 else "Queen"
    return [
        (orch, "We're here — noting your message. For heavy work, launch a mission from the hive dashboard."),
        (second, f"Echo locked in: «{preview}»"),
        (third, "Transcript updated; imitate top performers once the next task pollen lands."),
    ]


def _norm_agent_key(value: str) -> str:
    """Normalize agent label for simple @mention matching."""

    return "".join(ch for ch in value.lower() if ch.isalnum())


def _resolve_target_agents(user_text: str, agent_names: list[str]) -> tuple[list[str], str]:
    """Resolve @agent mentions to an explicit speaking roster and cleaned prompt text."""

    mentions = re.findall(r"@([A-Za-z0-9][A-Za-z0-9_-]{1,31})", user_text)
    if not mentions:
        return (agent_names, user_text.strip())
    by_key: dict[str, str] = {_norm_agent_key(name): name for name in agent_names}
    selected: list[str] = []
    for token in mentions:
        match = by_key.get(_norm_agent_key(token))
        if match and match not in selected:
            selected.append(match)
    cleaned = re.sub(r"(?<!\w)@[A-Za-z0-9][A-Za-z0-9_-]{1,31}\b", "", user_text).strip()
    return (selected or agent_names, cleaned or user_text.strip())


async def _run_ballroom_user_chat_reply(session_id: uuid.UUID, user_text: str) -> None:
    """React to Ballroom operator text over wired agents (+ LLM when keys exist)."""

    if not await ballroom_redis.ballroom_has_capsule(session_id):
        return

    clipped = user_text.strip()[:12_000]
    if not clipped:
        return

    try:
        async with async_session() as session:
            agent_rows = list(
                (
                    await session.execute(
                        select(Agent)
                        .where(Agent.status.in_((AgentStatus.IDLE, AgentStatus.RUNNING)))
                        .order_by(Agent.name)
                        .limit(8),
                    )
                )
                .scalars()
                .all(),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ballroom.chat_agents_failed",
            session_id=str(session_id),
            task_id=f"ballroom-chat-{session_id}",
            error=str(exc),
        )
        await _emit_placeholder_lines(session_id, [("System", f"Hive lookup hiccup — try again shortly. ({type(exc).__name__})")])
        return

    agent_names = [a.name for a in agent_rows]
    default_roster = agent_names or ["Orchestrator", "Scout", "Queen"]
    target_agents, cleaned_text = _resolve_target_agents(clipped, default_roster)
    prompt_text = cleaned_text[:12_000]

    if not _llm_credentials_configured():
        await _emit_placeholder_lines(session_id, _fallback_chat_lines(target_agents, prompt_text))
        return

    router = LiteLLMRouter()
    roster = ", ".join(target_agents[:7])
    prompt = "\n".join(
        [
            f"Agents participating: {roster}",
            "The human ballroom operator says:",
            f"\"{prompt_text}\"",
            "",
            "Reply with EXACTLY 3-5 lines only, each line formatted as:",
            "AGENT_NAME: short reaction (<=120 chars; stay in-character; hive/bee metaphors ok).",
            "Use ONLY agent names from the participating list.",
        ],
    )

    try:
        async with async_session() as session:
            raw_text, _cost = await router.decompose(
                session,
                system_prompt=(
                    "You simulate a live ballroom swarm answering a human chat message. "
                    "Be terse, helpful, upbeat. Plain text only - no Markdown fences."
                ),
                user_payload=prompt,
                swarm_id=str(session_id),
                task_id=f"ballroom-chat-{session_id}",
            )
        lines_out: list[tuple[str, str]] = []
        allowed = set(target_agents)
        for ln in raw_text.splitlines():
            chunk = ln.strip()
            if ":" not in chunk or len(chunk) < 6:
                continue
            speaker, utter = chunk.split(":", 1)
            speaker_clean = speaker.strip()
            utter_clean = utter.strip()
            if not utter_clean:
                continue
            if speaker_clean not in allowed:
                continue
            lines_out.append((speaker_clean, utter_clean))

        if not lines_out:
            raise RuntimeError("model returned no NAME: utterance pairs")

        await _emit_placeholder_lines(session_id, lines_out[:6])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ballroom.chat_llm_failed",
            session_id=str(session_id),
            task_id=f"ballroom-chat-{session_id}",
            error=str(exc),
        )
        await _emit_placeholder_lines(session_id, _fallback_chat_lines(target_agents, prompt_text))


async def _emit_server_tts_event(
    session_id: uuid.UUID,
    *,
    text: str,
    agent: str,
    mode: Literal["swarm", "orchestrator"],
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto",
    latency_mode: Literal["balanced", "fast"] = "balanced",
    tts_voice_id: str | None = None,
    tts_language: str | None = None,
    tts_tone: str | None = None,
) -> None:
    """Synthesize speech server-side and fan out audio payload."""

    try:
        audio = await synthesize_speech(
            text=text,
            preferred_provider=preferred_tts_provider,
            latency_mode=latency_mode,
            tts_voice_id=tts_voice_id,
            tts_language=tts_language,
            tts_tone=tts_tone,
        )
    except VoiceServiceError as exc:
        logger.warning(
            "ballroom.voice_tts_emit_failed",
            session_id=str(session_id),
            task_id=f"ballroom-tts-{session_id}",
            error=str(exc),
        )
        await ballroom_dispatch_fanout(
            session_id,
            {
                "type": "ballroom.voice_audio_error",
                "session_id": str(session_id),
                "agent": agent,
                "mode": mode,
                "detail": str(exc),
            },
        )
        return

    await ballroom_dispatch_fanout(
        session_id,
        {
            "type": "ballroom.voice_audio",
            "session_id": str(session_id),
            "agent": agent,
            "mode": mode,
            "provider": audio.provider,
            "content_type": audio.content_type,
            "audio_base64": audio.audio_base64,
            "text": text,
        },
    )


async def _emit_ballroom_thinking(session_id: uuid.UUID) -> None:
    """Tell clients the orchestrator is composing a reply (instant UX feedback)."""

    await ballroom_dispatch_fanout(
        session_id,
        {
            "type": "ballroom.thinking",
            "agent": "Orchestrator",
            "timestamp": datetime.now(tz=UTC).isoformat(),
        },
    )


async def _run_ballroom_orchestrator_reply(
    session_id: uuid.UUID,
    user_text: str,
    *,
    preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto",
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto",
    latency_mode: Literal["balanced", "fast"] = "balanced",
    tts_voice_id: str | None = None,
    tts_language: str | None = None,
    tts_tone: str | None = None,
) -> None:
    """Generate a direct orchestrator reply suitable for voice-chat mode."""

    if not await ballroom_redis.ballroom_has_capsule(session_id):
        return
    clipped = user_text.strip()[:8_000]
    if not clipped:
        return
    cap = await ballroom_redis.ballroom_load_capsule(session_id)
    chat_prompt = _read_capsule_chat_prompt(cap)
    if not _llm_credentials_configured():
        await append_ballroom_transcript_line_public(
            session_id,
            "Orchestrator",
            "Acknowledged. I am in direct voice lane mode and ready to coordinate your next step.",
            broadcast=True,
        )
        return
    router = LiteLLMRouter()
    assignment_line = (
        f"[Session assignment active: {chat_prompt['label']}]" if chat_prompt else ""
    )
    prompt = "\n".join(
        [
            part
            for part in (
                assignment_line,
                "Operator says:",
                clipped,
                "",
                (
                    "Reply as ORCHESTRATOR in one concise paragraph "
                    "(max 2 sentences when latency_mode=fast, else max 4), pragmatic and action-oriented."
                ),
                f"latency_mode={latency_mode}",
            )
            if part
        ],
    )
    orch_system = _orchestrator_system_prompt(chat_prompt)
    try:
        grok_ready = bool(provider_effective_grok())
        if latency_mode == "fast" and grok_ready:
            reply = await grok_ballroom_reply_fast(user_text=clipped, system_prompt=orch_system)
        else:
            try:
                async with async_session() as session:
                    strict_grok_only = preferred_stt_provider == "grok" and preferred_tts_provider == "grok"
                    raw_text, _cost = await router.decompose_ballroom(
                        session,
                        system_prompt=orch_system,
                        user_payload=prompt,
                        swarm_id=str(session_id),
                        task_id=f"ballroom-orchestrator-{session_id}",
                        latency_mode=latency_mode,
                        strict_grok_only=strict_grok_only,
                    )
                reply = raw_text.strip()
            except Exception as router_exc:
                if grok_ready:
                    logger.warning(
                        "ballroom.orchestrator_router_fallback",
                        session_id=str(session_id),
                        task_id=f"ballroom-orchestrator-{session_id}",
                        error=str(router_exc),
                    )
                    reply = await grok_ballroom_reply_fast(user_text=clipped, system_prompt=orch_system)
                else:
                    raise router_exc from router_exc
        if not reply:
            raise RuntimeError("orchestrator_reply_empty")
        clean_reply = reply[:420] if latency_mode == "fast" else reply[:900]
        await append_ballroom_transcript_line_public(session_id, "Orchestrator", clean_reply, broadcast=True)

        async def _tts_background() -> None:
            try:
                await _emit_server_tts_event(
                    session_id,
                    text=clean_reply,
                    agent="Orchestrator",
                    mode="orchestrator",
                    preferred_tts_provider=preferred_tts_provider,
                    latency_mode=latency_mode,
                    tts_voice_id=tts_voice_id,
                    tts_language=tts_language,
                    tts_tone=tts_tone,
                )
            except Exception as tts_exc:  # noqa: BLE001
                logger.warning(
                    "ballroom.orchestrator_tts_failed",
                    session_id=str(session_id),
                    task_id=f"ballroom-orchestrator-{session_id}",
                    error=str(tts_exc),
                )

        asyncio.create_task(_tts_background())
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ballroom.orchestrator_reply_failed",
            session_id=str(session_id),
            task_id=f"ballroom-orchestrator-{session_id}",
            error=str(exc),
        )
        await append_ballroom_transcript_line_public(
            session_id,
            "Orchestrator",
            "I could not reach the LLM right now. Check API keys in Settings → LLM keys, then retry.",
            broadcast=True,
        )
        return


async def _handle_user_chat_message(
    session_id: uuid.UUID,
    text: str,
    mode: Literal["swarm", "orchestrator"],
    *,
    preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto",
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto",
    latency_mode: Literal["balanced", "fast"] = "balanced",
    tts_voice_id: str | None = None,
    tts_language: str | None = None,
    tts_tone: str | None = None,
) -> None:
    """Persist user line server-side (no broadcast) then fan out agent chatter."""

    if not await ballroom_redis.ballroom_has_capsule(session_id):
        return

    clipped = text.strip()
    if not clipped:
        return

    logger.info(
        "ballroom.user_message",
        session_id=str(session_id),
        swarm_id=str(session_id),
        task_id=f"ballroom-chat-{session_id}",
        text_chars=len(clipped),
    )

    await append_silent_chat_line_public(session_id, "You", clipped)
    if mode == "orchestrator":
        await _emit_ballroom_thinking(session_id)
        await _run_ballroom_orchestrator_reply(
            session_id,
            clipped,
            preferred_stt_provider=preferred_stt_provider,
            preferred_tts_provider=preferred_tts_provider,
            latency_mode=latency_mode,
            tts_voice_id=tts_voice_id,
            tts_language=tts_language,
            tts_tone=tts_tone,
        )
        return
    await _run_ballroom_user_chat_reply(session_id, clipped)


def _spawn_user_chat_task(
    session_id: uuid.UUID,
    text: str,
    mode: Literal["swarm", "orchestrator"] = "swarm",
    preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto",
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto",
    latency_mode: Literal["balanced", "fast"] = "balanced",
    tts_voice_id: str | None = None,
    tts_language: str | None = None,
    tts_tone: str | None = None,
) -> None:
    """Fire-and-forget user chat pipeline so HTTP/WS handlers return quickly."""

    async def _runner() -> None:
        try:
            await _handle_user_chat_message(
                session_id,
                text,
                mode,
                preferred_stt_provider=preferred_stt_provider,
                preferred_tts_provider=preferred_tts_provider,
                latency_mode=latency_mode,
                tts_voice_id=tts_voice_id,
                tts_language=tts_language,
                tts_tone=tts_tone,
            )
        except Exception as exc:  # noqa: BLE001 — keep ballroom warm on chat errors
            logger.warning(
                "ballroom.user_chat_runner_failed",
                session_id=str(session_id),
                swarm_id=str(session_id),
                task_id=f"ballroom-chat-{session_id}",
                error=str(exc),
            )

    asyncio.create_task(_runner())


async def _handle_ws_voice_chunk(
    *,
    session_id: uuid.UUID,
    inbound: dict[str, Any],
    actor: str | None,
) -> None:
    """Handle one websocket voice chunk entirely server-side."""

    audio_base64 = inbound.get("audio_base64")
    if not isinstance(audio_base64, str) or len(audio_base64) < 20 or len(audio_base64) > 8_000_000:
        await ballroom_dispatch_fanout(
            session_id,
            {"type": "ballroom.error", "detail": "voice_chunk_invalid_audio"},
        )
        return

    mime_type_raw = inbound.get("mime_type")
    mime_type = mime_type_raw if isinstance(mime_type_raw, str) and mime_type_raw.strip() else "audio/webm"
    language_raw = inbound.get("language")
    language = language_raw if isinstance(language_raw, str) and language_raw.strip() else "auto"
    mode_raw = inbound.get("target_mode")
    mode: Literal["swarm", "orchestrator"] = "orchestrator" if mode_raw == "orchestrator" else "swarm"
    preferred_stt_raw = inbound.get("preferred_stt_provider")
    preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto"
    if preferred_stt_raw in {"auto", "grok", "deepgram", "openai"}:
        preferred_stt_provider = preferred_stt_raw
    preferred_tts_raw = inbound.get("preferred_tts_provider")
    preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto"
    if preferred_tts_raw in {"auto", "grok", "elevenlabs", "openai"}:
        preferred_tts_provider = preferred_tts_raw
    latency_mode_raw = inbound.get("latency_mode")
    latency_mode: Literal["balanced", "fast"] = "balanced"
    if latency_mode_raw in {"balanced", "fast"}:
        latency_mode = latency_mode_raw
    tts_voice_id_raw = inbound.get("tts_voice_id")
    tts_voice_id = tts_voice_id_raw.strip() if isinstance(tts_voice_id_raw, str) and tts_voice_id_raw.strip() else None
    tts_language_raw = inbound.get("tts_language")
    tts_language = tts_language_raw.strip() if isinstance(tts_language_raw, str) and tts_language_raw.strip() else None
    tts_tone_raw = inbound.get("tts_tone")
    tts_tone = tts_tone_raw.strip() if isinstance(tts_tone_raw, str) and tts_tone_raw.strip() else None
    dispatch_to_agents = bool(inbound.get("dispatch_to_agents", True))

    logger.info(
        "ballroom.voice_chunk_received",
        actor=actor,
        session_id=str(session_id),
        swarm_id=str(session_id),
        task_id=f"ballroom-voice-{session_id}",
        mime_type=mime_type,
        mode=mode,
    )

    try:
        out = await transcribe_audio(
            audio_base64=audio_base64,
            mime_type=mime_type,
            language=_resolve_stt_language(language=language, tts_language=tts_language),
            preferred_provider=preferred_stt_provider,
            latency_mode=latency_mode,
        )
    except VoiceEmptyTranscriptionError as exc:
        logger.info(
            "ballroom.voice_chunk_silent",
            actor=actor,
            session_id=str(session_id),
            detail=str(exc),
        )
        await ballroom_dispatch_fanout(
            session_id,
            {"type": "ballroom.voice_no_speech", "detail": "No speech detected — speak louder or move closer to the mic."},
        )
        return
    except VoiceServiceError as exc:
        await ballroom_dispatch_fanout(
            session_id,
            {"type": "ballroom.error", "detail": str(exc), "stage": "voice_transcribe"},
        )
        return

    await append_ballroom_transcript_line_public(session_id, "You", out.text, broadcast=True)
    await ballroom_dispatch_fanout(
        session_id,
        {
            "type": "ballroom.voice_transcribed",
            "session_id": str(session_id),
            "text": out.text,
            "provider": out.provider,
            "language": out.language,
        },
    )
    if dispatch_to_agents:
        _spawn_user_chat_task(
            session_id,
            out.text,
            mode,
            preferred_stt_provider=preferred_stt_provider,
            preferred_tts_provider=preferred_tts_provider,
            latency_mode=latency_mode,
            tts_voice_id=tts_voice_id,
            tts_language=tts_language,
            tts_tone=tts_tone,
        )


def _spawn_ws_voice_chunk_task(
    *,
    session_id: uuid.UUID,
    inbound: dict[str, Any],
    actor: str | None,
) -> None:
    """Fire-and-forget websocket voice chunk processing."""

    async def _runner() -> None:
        try:
            await _handle_ws_voice_chunk(session_id=session_id, inbound=inbound, actor=actor)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "ballroom.voice_chunk_runner_failed",
                actor=actor,
                session_id=str(session_id),
                swarm_id=str(session_id),
                task_id=f"ballroom-voice-{session_id}",
                error=str(exc),
            )

    asyncio.create_task(_runner())


@_router.websocket("/live")
async def hive_live_channel(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    """Hive dashboard stream emitting periodic swarm snapshots."""

    await websocket.accept()
    subject = _decode_ws_subject(websocket, token)
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
    await ballroom_redis.ballroom_ensure_capsule(session_id)
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
    await ballroom_redis.ballroom_ensure_capsule(capsule_id)
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


@_bb_router.post("/message", status_code=status.HTTP_202_ACCEPTED, summary="Send Ballroom chat — agents reply asynchronously")
async def ballroom_post_chat(body: BallroomChatMessageBody, subject: JwtSubject) -> dict[str, object]:
    """Queue user text; responses stream as ballroom.transcript on the websocket."""

    _SESSION_CHANNELS.setdefault(body.session_id, set())
    await ballroom_redis.ballroom_ensure_capsule(body.session_id)
    logger.info(
        "ballroom.message_accepted",
        actor=subject,
        session_id=str(body.session_id),
        swarm_id=str(body.session_id),
        task_id=f"ballroom-chat-{body.session_id}",
    )
    _spawn_user_chat_task(
        body.session_id,
        body.text,
        body.mode,
        preferred_stt_provider=body.preferred_stt_provider,
        preferred_tts_provider=body.preferred_tts_provider,
        latency_mode=body.latency_mode,
        tts_voice_id=body.tts_voice_id,
        tts_language=body.tts_language,
        tts_tone=body.tts_tone,
    )
    return {"ok": True, "session_id": str(body.session_id)}


@_bb_router.post("/voice/transcribe", status_code=status.HTTP_200_OK, summary="Transcribe operator voice chunk (STT)")
async def ballroom_transcribe_voice(body: BallroomVoiceTranscribeBody, subject: JwtSubject) -> dict[str, object]:
    """Transcribe one voice chunk and optionally dispatch it as operator chat."""

    logger.info("ballroom.voice_transcribe.request", actor=subject, session_id=str(body.session_id or "none"))
    try:
        out = await transcribe_audio(
            audio_base64=body.audio_base64,
            mime_type=body.mime_type,
            language=_resolve_stt_language(language=body.language, tts_language=body.tts_language),
            preferred_provider=body.preferred_stt_provider,
            latency_mode=body.latency_mode,
        )
    except VoiceEmptyTranscriptionError as exc:
        return {"ok": False, "text": "", "detail": str(exc), "skipped": True}
    except VoiceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    result: dict[str, object] = {
        "ok": True,
        "text": out.text,
        "provider": out.provider,
        "language": out.language,
    }
    if body.session_id is not None:
        _SESSION_CHANNELS.setdefault(body.session_id, set())
        await ballroom_redis.ballroom_ensure_capsule(body.session_id)
        await append_ballroom_transcript_line_public(body.session_id, "You", out.text, broadcast=True)
        if body.dispatch_to_agents:
            await _emit_ballroom_thinking(body.session_id)
            _spawn_user_chat_task(
                body.session_id,
                out.text,
                body.target_mode,
                preferred_stt_provider=body.preferred_stt_provider,
                preferred_tts_provider=body.preferred_tts_provider,
                latency_mode=body.latency_mode,
                tts_voice_id=body.tts_voice_id,
                tts_language=body.tts_language,
                tts_tone=body.tts_tone,
            )
        result["session_id"] = str(body.session_id)
    return result


@_bb_router.post("/voice/live-token", status_code=status.HTTP_200_OK, summary="Mint xAI Voice Agent client secret for live call")
async def ballroom_voice_live_token(subject: JwtSubject) -> dict[str, object]:
    """Return ephemeral token for browser → xAI realtime voice WebSocket (Grok-style live chat)."""

    logger.info("ballroom.voice_live_token.request", actor=subject)
    try:
        token_body = await mint_voice_live_client_secret()
    except XaiVoiceLiveError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    model = settings.ballroom_voice_live_model.strip() or "grok-voice-latest"
    secret = token_body.get("value")
    return {
        "ok": True,
        "client_secret": secret,
        "expires_at": token_body.get("expires_at"),
        "model": model,
        "ws_url": f"wss://api.x.ai/v1/realtime?model={model}",
    }


@_bb_router.post("/voice/synthesize", status_code=status.HTTP_200_OK, summary="Synthesize speech for ballroom reply (TTS)")
async def ballroom_synthesize_voice(body: BallroomVoiceSynthesizeBody, subject: JwtSubject) -> dict[str, object]:
    """Create TTS audio for one assistant/user-visible text."""

    logger.info("ballroom.voice_synthesize.request", actor=subject)
    try:
        out = await synthesize_speech(
            text=body.text,
            preferred_provider=body.preferred_tts_provider,
            latency_mode=body.latency_mode,
            tts_voice_id=body.tts_voice_id,
            tts_language=body.tts_language,
            tts_tone=body.tts_tone,
        )
    except VoiceServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return {
        "ok": True,
        "provider": out.provider,
        "content_type": out.content_type,
        "audio_base64": out.audio_base64,
    }


@_bb_router.get(
    "/voice/capabilities",
    response_model=BallroomVoiceCapabilitiesResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect runtime Ballroom voice STT/TTS capabilities",
)
async def ballroom_voice_capabilities(_subject: JwtSubject) -> BallroomVoiceCapabilitiesResponse:
    """Expose effective voice pipeline capabilities for operator UX."""

    return _voice_capabilities()


@_bb_router.get("/session/{session_id}")
async def get_ballroom_session(session_id: uuid.UUID, _subject: JwtSubject) -> dict[str, object]:
    """Return transcript capsule (Redis-backed operator view)."""

    try:
        cap = await ballroom_redis.ballroom_load_capsule(session_id)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found") from None
    return dict(cap)


@_bb_router.get("/sessions")
async def list_ballroom_sessions(_subject: JwtSubject) -> dict[str, object]:
    """Lightweight ballroom registry from Redis SCAN (bounded)."""

    rows: list[dict[str, object]] = []
    limit = int(getattr(settings, "ballroom_sessions_list_limit", 128))
    for sid in await ballroom_redis.ballroom_scan_recent_session_ids(limit=limit):
        try:
            cap = await ballroom_redis.ballroom_load_capsule(sid)
        except RuntimeError:
            continue
        transcript = cap.get("transcript", [])
        preview = ""
        if isinstance(transcript, list):
            for row in transcript:
                if not isinstance(row, dict):
                    continue
                agent = row.get("agent")
                text = row.get("text")
                if not isinstance(text, str):
                    continue
                stripped = text.strip()
                if not stripped:
                    continue
                if agent == "You":
                    preview = stripped
                    break
                if not preview and agent not in {"System", "system"}:
                    preview = stripped
        if len(preview) > 80:
            preview = preview[:80].rstrip() + "…"
        rows.append(
            {
                "session_id": str(sid),
                "started_at": cap.get("started_at"),
                "message_count": len(transcript) if isinstance(transcript, list) else 0,
                "status": cap.get("status"),
                "title": cap.get("title"),
                "preview": preview,
                "pinned": bool(cap.get("pinned", False)),
            },
        )
    return {"sessions": rows}


@_bb_router.patch("/session/{session_id}/meta", status_code=status.HTTP_200_OK)
async def update_ballroom_session_meta(
    session_id: uuid.UUID,
    body: BallroomSessionMetaBody,
    _subject: JwtSubject,
) -> dict[str, object]:
    """Update display metadata (title/pin) for one session."""

    try:
        cap = await ballroom_redis.ballroom_load_capsule(session_id)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found") from None
    if body.title is not None:
        cap["title"] = body.title.strip()
    if body.pinned is not None:
        cap["pinned"] = bool(body.pinned)
    await ballroom_redis.ballroom_save_capsule(session_id, cap)
    return {
        "ok": True,
        "session_id": str(session_id),
        "title": cap.get("title"),
        "pinned": bool(cap.get("pinned", False)),
    }


@_bb_router.post("/session/{session_id}/prompt", status_code=status.HTTP_200_OK)
async def apply_ballroom_session_prompt(
    session_id: uuid.UUID,
    body: BallroomChatPromptBody,
    _subject: JwtSubject,
) -> dict[str, object]:
    """Apply a quick-prompt assignment brief to the active Ballroom session."""

    try:
        cap = await ballroom_redis.ballroom_load_capsule(session_id)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found") from None

    label = body.label.strip()
    text = body.text.strip()
    cap["chat_prompt"] = {
        "label": label,
        "text": text,
        "applied_at": datetime.now(tz=UTC).isoformat(),
    }
    await ballroom_redis.ballroom_save_capsule(session_id, cap)
    event: dict[str, Any] = {
        "type": "ballroom.prompt_applied",
        "chat_prompt": cap["chat_prompt"],
        "agent": "System",
        "text": f"Assignment applied: {label}",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    await ballroom_dispatch_fanout(session_id, event)
    logger.info(
        "ballroom.prompt_applied",
        session_id=str(session_id),
        swarm_id=str(session_id),
        task_id=f"ballroom-prompt-{session_id}",
        label=label,
    )
    return {"ok": True, "session_id": str(session_id), "chat_prompt": cap["chat_prompt"]}


@_bb_router.delete("/session/{session_id}/prompt", status_code=status.HTTP_200_OK)
async def clear_ballroom_session_prompt(session_id: uuid.UUID, _subject: JwtSubject) -> dict[str, object]:
    """Remove the active session assignment brief."""

    try:
        cap = await ballroom_redis.ballroom_load_capsule(session_id)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found") from None

    cap.pop("chat_prompt", None)
    await ballroom_redis.ballroom_save_capsule(session_id, cap)
    event: dict[str, Any] = {
        "type": "ballroom.prompt_cleared",
        "agent": "System",
        "text": "Session assignment cleared.",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    await ballroom_dispatch_fanout(session_id, event)
    return {"ok": True, "session_id": str(session_id)}


@_bb_router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def delete_ballroom_session(session_id: uuid.UUID, _subject: JwtSubject) -> dict[str, object]:
    """Delete one session capsule from history."""

    await ballroom_redis.ballroom_delete_capsule(session_id)
    return {"ok": True, "session_id": str(session_id)}


async def _ballroom_socket_loop(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str | None,
) -> None:
    """Shared consumer for ballroom websocket sessions."""

    await websocket.accept()
    subject = _decode_ws_subject(websocket, token)
    if subject is None and settings.ballroom_guest_ws:
        subject = "ballroom-demo-guest"
    if subject is None:
        await websocket.send_json({"type": "ballroom.error", "detail": "jwt_required"})
        await websocket.close(code=1008, reason="auth")
        return

    cap = await ballroom_redis.ballroom_ensure_capsule(session_id)
    _maybe_start_fanout_worker(session_id)
    sockets = _SESSION_CHANNELS.setdefault(session_id, set())
    sockets.add(websocket)

    participant = str(id(websocket))
    caps = cap.setdefault("participants", [])
    if isinstance(caps, list) and participant not in caps:
        caps.append(participant)
    await ballroom_redis.ballroom_save_capsule(session_id, cap)

    hist = {
        "type": "history",
        "messages": list(cap.get("transcript", [])),
        "chat_prompt": _read_capsule_chat_prompt(cap),
    }
    await websocket.send_json(hist)

    ready_msg = json.dumps(
        {
            "type": "ballroom.ready",
            "session_id": str(session_id),
            "speaker": "hive-conductor",
            "text": "Ballroom ready — speak or type to reach the Orchestrator.",
        },
    )
    await websocket.send_text(ready_msg)

    # Skip auto LLM discussion on connect — it competes for latency and spams the chat lane.

    try:
        while True:
            event = await websocket.receive()
            if event.get("type") == "websocket.disconnect":
                break
            raw = event.get("text")
            if not isinstance(raw, str):
                continue
            try:
                inbound = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(inbound, dict):
                continue
            msg_type = inbound.get("type")
            if msg_type not in {"user_message", "voice_chunk"}:
                continue
            sid_raw = inbound.get("session_id")
            if sid_raw not in (None, ""):
                try:
                    if uuid.UUID(str(sid_raw)) != session_id:
                        continue
                except ValueError:
                    continue
            if msg_type == "voice_chunk":
                _spawn_ws_voice_chunk_task(session_id=session_id, inbound=inbound, actor=subject)
                continue
            text_val = inbound.get("text")
            if not isinstance(text_val, str) or not text_val.strip():
                continue
            mode_raw = inbound.get("mode")
            mode: Literal["swarm", "orchestrator"] = "orchestrator" if mode_raw == "orchestrator" else "swarm"
            preferred_tts_raw = inbound.get("preferred_tts_provider")
            preferred_tts_provider: Literal["auto", "grok", "elevenlabs", "openai"] = "auto"
            if preferred_tts_raw in {"auto", "grok", "elevenlabs", "openai"}:
                preferred_tts_provider = preferred_tts_raw
            preferred_stt_raw = inbound.get("preferred_stt_provider")
            preferred_stt_provider: Literal["auto", "grok", "deepgram", "openai"] = "auto"
            if preferred_stt_raw in {"auto", "grok", "deepgram", "openai"}:
                preferred_stt_provider = preferred_stt_raw
            latency_mode_raw = inbound.get("latency_mode")
            latency_mode: Literal["balanced", "fast"] = "balanced"
            if latency_mode_raw in {"balanced", "fast"}:
                latency_mode = latency_mode_raw
            tts_voice_id_raw = inbound.get("tts_voice_id")
            tts_voice_id = tts_voice_id_raw.strip() if isinstance(tts_voice_id_raw, str) and tts_voice_id_raw.strip() else None
            tts_language_raw = inbound.get("tts_language")
            tts_language = tts_language_raw.strip() if isinstance(tts_language_raw, str) and tts_language_raw.strip() else None
            tts_tone_raw = inbound.get("tts_tone")
            tts_tone = tts_tone_raw.strip() if isinstance(tts_tone_raw, str) and tts_tone_raw.strip() else None
            _spawn_user_chat_task(
                session_id,
                text_val,
                mode,
                preferred_stt_provider=preferred_stt_provider,
                preferred_tts_provider=preferred_tts_provider,
                latency_mode=latency_mode,
                tts_voice_id=tts_voice_id,
                tts_language=tts_language,
                tts_tone=tts_tone,
            )
    except WebSocketDisconnect:
        pass
    finally:
        sockets.discard(websocket)
        try:
            refreshed = await ballroom_redis.ballroom_load_capsule(session_id)
            plist = refreshed.get("participants")
            if isinstance(plist, list) and participant in plist:
                plist.remove(participant)
            await ballroom_redis.ballroom_save_capsule(session_id, refreshed)
        except RuntimeError:
            pass

        if not sockets:
            _SESSION_CHANNELS.pop(session_id, None)
            _cancel_fanout_worker(session_id)


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


__all__ = ["append_ballroom_orchestrator_out_public", "append_ballroom_transcript_line_public", "ballroom_router", "get_realtime_router"]
ballroom_router = _bb_router
