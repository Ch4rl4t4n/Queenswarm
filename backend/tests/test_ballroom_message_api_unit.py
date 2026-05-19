"""REST acceptance for Ballroom operator chat ingestion."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services import ballroom_store
from app.presentation.api.routers import realtime_ballroom
from app.main import app
from app.presentation.api.deps import require_subject


@pytest.fixture
def ballroom_auth_fixture() -> None:
    """Inject a deterministic JWT subject."""

    app.dependency_overrides[require_subject] = lambda: "pytest-ballroom-operator"
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ballroom_message_creates_capsule_when_session_only_known_from_url(
    ballroom_auth_fixture: None,
) -> None:
    """Operator chat succeeds before the websocket handshake finishes (matches /ws lax capsule policy)."""

    sid = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ballroom/message",
            json={"session_id": str(sid), "text": "hello swarm"},
        )
    assert resp.status_code == 202
    assert await ballroom_store.ballroom_has_capsule(sid)


@pytest.mark.asyncio
async def test_ballroom_message_accepts_text_for_known_session(ballroom_auth_fixture: None) -> None:
    """Minted ballroom capsules accept queued chat and persist the operator line asynchronously."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        started = await client.post("/api/v1/ballroom/start", json={})
        assert started.status_code == 201
        capsule = started.json()
        sid_raw = capsule.get("session_id")
        assert isinstance(sid_raw, str)

        queued = await client.post(
            "/api/v1/ballroom/message",
            json={"session_id": sid_raw, "text": "need something done"},
        )
        assert queued.status_code == 202
        assert queued.json().get("ok") is True

    sid_uuid = uuid.UUID(str(sid_raw))
    persisted = False
    for _ in range(80):
        if not await ballroom_store.ballroom_has_capsule(sid_uuid):
            await asyncio.sleep(0.025)
            continue
        cap = await ballroom_store.ballroom_load_capsule(sid_uuid)
        transcripts = cap.get("transcript", []) if isinstance(cap, dict) else []
        if any(isinstance(row, dict) and row.get("agent") == "You" for row in transcripts):
            persisted = True
            break
        await asyncio.sleep(0.025)
    assert persisted, "Expected server-side transcript row for operator message."


@pytest.mark.asyncio
async def test_ballroom_session_meta_patch_and_list(ballroom_auth_fixture: None) -> None:
    """Session list should include patched title/pinned metadata."""

    sid = uuid.uuid4()
    await ballroom_store.ballroom_ensure_capsule(sid)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        patched = await client.patch(
            f"/api/v1/ballroom/session/{sid}/meta",
            json={"title": "My voice plan", "pinned": True},
        )
        assert patched.status_code == 200
        listed = await client.get("/api/v1/ballroom/sessions")

    assert listed.status_code == 200
    payload = listed.json()
    sessions = payload.get("sessions", [])
    row = next((item for item in sessions if item.get("session_id") == str(sid)), None)
    assert row is not None
    assert row.get("title") == "My voice plan"
    assert row.get("pinned") is True


@pytest.mark.asyncio
async def test_ballroom_session_prompt_apply_and_clear(ballroom_auth_fixture: None) -> None:
    """Quick prompts persist as session assignment brief on the capsule."""

    sid = uuid.uuid4()
    await ballroom_store.ballroom_ensure_capsule(sid)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        applied = await client.post(
            f"/api/v1/ballroom/session/{sid}/prompt",
            json={"label": "Brainstorm", "text": "Always offer five options with pros and cons."},
        )
        assert applied.status_code == 200
        body = applied.json()
        assert body.get("ok") is True
        cp = body.get("chat_prompt")
        assert isinstance(cp, dict)
        assert cp.get("label") == "Brainstorm"

        cap = await ballroom_store.ballroom_load_capsule(sid)
        assert cap.get("chat_prompt", {}).get("text", "").startswith("Always offer")

        cleared = await client.delete(f"/api/v1/ballroom/session/{sid}/prompt")
        assert cleared.status_code == 200
        cap2 = await ballroom_store.ballroom_load_capsule(sid)
        assert "chat_prompt" not in cap2


@pytest.mark.asyncio
async def test_ballroom_session_delete_removes_capsule(ballroom_auth_fixture: None) -> None:
    """Deleting a session should remove its capsule from storage."""

    sid = uuid.uuid4()
    await ballroom_store.ballroom_ensure_capsule(sid)
    assert await ballroom_store.ballroom_has_capsule(sid)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        deleted = await client.delete(f"/api/v1/ballroom/session/{sid}")

    assert deleted.status_code == 200
    assert not await ballroom_store.ballroom_has_capsule(sid)


@pytest.mark.asyncio
async def test_ballroom_voice_transcribe_dispatches_transcript(monkeypatch: pytest.MonkeyPatch, ballroom_auth_fixture: None) -> None:
    """Voice STT endpoint appends user transcript and can dispatch the agent reply loop."""

    sid = uuid.uuid4()
    dispatched: list[tuple[uuid.UUID, str, str]] = []

    class _FakeResult:
        text = "voice hello"
        provider = "pytest"
        language = "sk"

    async def _ok_transcribe(**_: object) -> _FakeResult:
        return _FakeResult()

    def _record_dispatch(
        session_id: uuid.UUID,
        text: str,
        mode: str = "swarm",
        preferred_stt_provider: str = "auto",
        preferred_tts_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> None:
        dispatched.append((session_id, text, mode, preferred_tts_provider, latency_mode))

    monkeypatch.setattr(realtime_ballroom, "transcribe_audio", _ok_transcribe)
    monkeypatch.setattr(realtime_ballroom, "_spawn_user_chat_task", _record_dispatch)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ballroom/voice/transcribe",
            json={
                "session_id": str(sid),
                "audio_base64": "Zm9vYmFyYmF6YmF6YmF6",
                "mime_type": "audio/webm",
                "dispatch_to_agents": True,
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["text"] == "voice hello"
    cap = await ballroom_store.ballroom_load_capsule(sid)
    rows = cap.get("transcript", [])
    assert any(isinstance(row, dict) and row.get("agent") == "You" and row.get("text") == "voice hello" for row in rows)
    assert dispatched == [(sid, "voice hello", "swarm", "auto", "balanced")]


@pytest.mark.asyncio
async def test_ballroom_voice_synthesize_returns_audio(monkeypatch: pytest.MonkeyPatch, ballroom_auth_fixture: None) -> None:
    """Voice TTS endpoint proxies synthesized audio bytes as base64 payload."""

    class _S:
        provider = "pytest-tts"
        content_type = "audio/mpeg"
        audio_base64 = "dGVzdA=="

    async def _fake_synthesize(
        *,
        text: str,
        preferred_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> _S:
        assert text == "Ahoj swarm"
        assert preferred_provider == "auto"
        assert latency_mode == "balanced"
        return _S()

    monkeypatch.setattr(realtime_ballroom, "synthesize_speech", _fake_synthesize)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/ballroom/voice/synthesize", json={"text": "Ahoj swarm"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["provider"] == "pytest-tts"
    assert payload["audio_base64"] == "dGVzdA=="


@pytest.mark.asyncio
async def test_ballroom_voice_capabilities_endpoint(monkeypatch: pytest.MonkeyPatch, ballroom_auth_fixture: None) -> None:
    """Voice capabilities endpoint should return backend runtime flags."""

    def _fake_caps() -> realtime_ballroom.BallroomVoiceCapabilitiesResponse:
        return realtime_ballroom.BallroomVoiceCapabilitiesResponse(
            ok=True,
            voice_enabled=True,
            stt_enabled=True,
            tts_enabled=True,
            stt_provider="openai_whisper",
            tts_provider="openai_tts",
            detail=None,
        )

    monkeypatch.setattr(realtime_ballroom, "_voice_capabilities", _fake_caps)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/ballroom/voice/capabilities")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["stt_enabled"] is True
    assert payload["tts_enabled"] is True


@pytest.mark.asyncio
async def test_ballroom_message_accepts_orchestrator_mode(
    monkeypatch: pytest.MonkeyPatch,
    ballroom_auth_fixture: None,
) -> None:
    """Message endpoint should pass explicit orchestrator mode to async runner."""

    sid = uuid.uuid4()
    captured: list[tuple[uuid.UUID, str, str]] = []

    def _capture(
        session_id: uuid.UUID,
        text: str,
        mode: str = "swarm",
        preferred_stt_provider: str = "auto",
        preferred_tts_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> None:
        captured.append((session_id, text, mode, preferred_tts_provider, latency_mode))

    monkeypatch.setattr(realtime_ballroom, "_spawn_user_chat_task", _capture)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ballroom/message",
            json={"session_id": str(sid), "text": "direct to orchestrator", "mode": "orchestrator"},
        )
    assert resp.status_code == 202
    assert captured == [(sid, "direct to orchestrator", "orchestrator", "auto", "balanced")]


@pytest.mark.asyncio
async def test_ballroom_message_passes_preferred_tts_provider(
    monkeypatch: pytest.MonkeyPatch,
    ballroom_auth_fixture: None,
) -> None:
    """Message endpoint should pass explicit TTS preference into async runner."""

    sid = uuid.uuid4()
    captured: list[tuple[uuid.UUID, str, str, str]] = []

    def _capture(
        session_id: uuid.UUID,
        text: str,
        mode: str = "swarm",
        preferred_stt_provider: str = "auto",
        preferred_tts_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> None:
        captured.append((session_id, text, mode, preferred_tts_provider, latency_mode))

    monkeypatch.setattr(realtime_ballroom, "_spawn_user_chat_task", _capture)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ballroom/message",
            json={
                "session_id": str(sid),
                "text": "speak with openai tts",
                "mode": "orchestrator",
                "preferred_tts_provider": "openai",
            },
        )
    assert resp.status_code == 202
    assert captured == [(sid, "speak with openai tts", "orchestrator", "openai", "balanced")]


@pytest.mark.asyncio
async def test_orchestrator_reply_emits_transcript_and_server_tts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Orchestrator mode should produce text transcript and server-side audio event."""

    sid = uuid.uuid4()
    await ballroom_store.ballroom_ensure_capsule(sid)
    transcript_calls: list[tuple[str, str]] = []
    tts_calls: list[str] = []
    background_coros: list[object] = []

    def _capture_create_task(coro: object) -> asyncio.Task[None]:
        background_coros.append(coro)
        loop = asyncio.get_running_loop()
        return loop.create_task(asyncio.sleep(0))

    @asynccontextmanager
    async def _fake_db_session() -> AsyncIterator[MagicMock]:
        yield MagicMock()

    class _FakeRouter:
        async def decompose_ballroom(self, *args: object, **kwargs: object) -> tuple[str, float]:
            return ("Proceed with step one now.", 0.01)

    async def _fake_append(
        session_id: uuid.UUID,
        agent: str,
        text: str,
        *,
        broadcast: bool = True,
    ) -> dict[str, object]:
        assert session_id == sid
        assert broadcast is True
        transcript_calls.append((agent, text))
        return {}

    async def _fake_emit(
        session_id: uuid.UUID,
        *,
        text: str,
        agent: str,
        mode: str,
        preferred_tts_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> None:
        assert session_id == sid
        assert agent == "Orchestrator"
        assert mode == "orchestrator"
        assert preferred_tts_provider == "auto"
        assert latency_mode == "balanced"
        tts_calls.append(text)

    monkeypatch.setattr(realtime_ballroom, "_llm_credentials_configured", lambda: True)
    monkeypatch.setattr(realtime_ballroom, "provider_effective_grok", lambda: "")
    monkeypatch.setattr(realtime_ballroom, "async_session", _fake_db_session)
    monkeypatch.setattr(realtime_ballroom, "LiteLLMRouter", _FakeRouter)
    monkeypatch.setattr(realtime_ballroom, "append_ballroom_transcript_line_public", _fake_append)
    monkeypatch.setattr(realtime_ballroom, "_emit_server_tts_event", _fake_emit)
    monkeypatch.setattr(realtime_ballroom.asyncio, "create_task", _capture_create_task)

    await realtime_ballroom._run_ballroom_orchestrator_reply(sid, "What is the next step?")
    for coro in background_coros:
        await coro  # type: ignore[misc]

    assert transcript_calls == [("Orchestrator", "Proceed with step one now.")]
    assert tts_calls == ["Proceed with step one now."]


@pytest.mark.asyncio
async def test_orchestrator_reply_fast_mode_uses_direct_grok_with_auto_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fast latency + auto STT/TTS must use direct Grok hop (not LiteLLM router)."""

    sid = uuid.uuid4()
    await ballroom_store.ballroom_ensure_capsule(sid)
    transcript_calls: list[tuple[str, str]] = []
    router_called = {"value": False}

    class _FakeRouter:
        async def decompose_ballroom(self, *args: object, **kwargs: object) -> tuple[str, float]:
            router_called["value"] = True
            return ("router should not run", 0.0)

    async def _fake_fast(*, user_text: str, system_prompt: str | None = None) -> str:
        assert user_text == "hello, whats up?"
        return "Hey, what's up?"

    async def _fake_append(
        session_id: uuid.UUID,
        agent: str,
        text: str,
        *,
        broadcast: bool = True,
    ) -> dict[str, object]:
        transcript_calls.append((agent, text))
        return {}

    async def _noop_tts(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(realtime_ballroom, "_llm_credentials_configured", lambda: True)
    monkeypatch.setattr(realtime_ballroom, "LiteLLMRouter", _FakeRouter)
    monkeypatch.setattr(realtime_ballroom, "provider_effective_grok", lambda: "xai-test-key")
    monkeypatch.setattr(realtime_ballroom, "grok_ballroom_reply_fast", _fake_fast)
    monkeypatch.setattr(realtime_ballroom, "append_ballroom_transcript_line_public", _fake_append)
    monkeypatch.setattr(realtime_ballroom, "_emit_server_tts_event", _noop_tts)

    await realtime_ballroom._run_ballroom_orchestrator_reply(
        sid,
        "hello, whats up?",
        preferred_stt_provider="auto",
        preferred_tts_provider="auto",
        latency_mode="fast",
    )

    assert router_called["value"] is False
    assert transcript_calls == [("Orchestrator", "Hey, what's up?")]


@pytest.mark.asyncio
async def test_ws_voice_chunk_transcribes_and_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    """WebSocket voice chunks should transcribe server-side and dispatch chat mode."""

    sid = uuid.uuid4()
    fanout_events: list[dict[str, object]] = []
    spawned: list[tuple[uuid.UUID, str, str]] = []
    transcript_rows: list[tuple[str, str]] = []

    class _T:
        text = "server transcript"
        provider = "pytest-whisper"
        language = "sk"

    async def _fake_transcribe(**_: object) -> _T:
        return _T()

    async def _fake_append(
        session_id: uuid.UUID,
        agent: str,
        text: str,
        *,
        broadcast: bool = True,
    ) -> dict[str, object]:
        assert session_id == sid
        assert broadcast is True
        transcript_rows.append((agent, text))
        return {}

    async def _fake_fanout(session_id: uuid.UUID, payload: dict[str, object]) -> None:
        assert session_id == sid
        fanout_events.append(payload)

    def _fake_spawn(
        session_id: uuid.UUID,
        text: str,
        mode: str = "swarm",
        preferred_stt_provider: str = "auto",
        preferred_tts_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> None:
        spawned.append((session_id, text, mode, preferred_tts_provider, latency_mode))

    monkeypatch.setattr(realtime_ballroom, "transcribe_audio", _fake_transcribe)
    monkeypatch.setattr(realtime_ballroom, "append_ballroom_transcript_line_public", _fake_append)
    monkeypatch.setattr(realtime_ballroom, "ballroom_dispatch_fanout", _fake_fanout)
    monkeypatch.setattr(realtime_ballroom, "_spawn_user_chat_task", _fake_spawn)

    await realtime_ballroom._handle_ws_voice_chunk(
        session_id=sid,
        inbound={
            "type": "voice_chunk",
            "audio_base64": "Zm9vYmFyYmF6YmF6YmF6YmF6YmF6YmF6",
            "mime_type": "audio/webm",
            "target_mode": "orchestrator",
            "dispatch_to_agents": True,
        },
        actor="pytest-user",
    )

    assert transcript_rows == [("You", "server transcript")]
    assert any(row.get("type") == "ballroom.voice_transcribed" for row in fanout_events)
    assert spawned == [(sid, "server transcript", "orchestrator", "auto", "balanced")]


@pytest.mark.asyncio
async def test_ws_voice_chunk_passes_provider_preferences(monkeypatch: pytest.MonkeyPatch) -> None:
    """WebSocket chunk pipeline should pass STT/TTS provider preferences through handlers."""

    sid = uuid.uuid4()
    observed_stt_preferences: list[str] = []
    spawned: list[tuple[uuid.UUID, str, str, str]] = []

    class _T:
        text = "provider aware transcript"
        provider = "pytest-whisper"
        language = "sk"

    async def _fake_transcribe(*, preferred_provider: str = "auto", **_: object) -> _T:
        observed_stt_preferences.append(preferred_provider)
        return _T()

    async def _fake_append(*args: object, **kwargs: object) -> dict[str, object]:
        return {}

    async def _fake_fanout(*args: object, **kwargs: object) -> None:
        return None

    def _fake_spawn(
        session_id: uuid.UUID,
        text: str,
        mode: str = "swarm",
        preferred_stt_provider: str = "auto",
        preferred_tts_provider: str = "auto",
        latency_mode: str = "balanced",
        tts_voice_id: str | None = None,
        tts_language: str | None = None,
        tts_tone: str | None = None,
    ) -> None:
        spawned.append((session_id, text, mode, preferred_tts_provider, latency_mode))

    monkeypatch.setattr(realtime_ballroom, "transcribe_audio", _fake_transcribe)
    monkeypatch.setattr(realtime_ballroom, "append_ballroom_transcript_line_public", _fake_append)
    monkeypatch.setattr(realtime_ballroom, "ballroom_dispatch_fanout", _fake_fanout)
    monkeypatch.setattr(realtime_ballroom, "_spawn_user_chat_task", _fake_spawn)

    await realtime_ballroom._handle_ws_voice_chunk(
        session_id=sid,
        inbound={
            "type": "voice_chunk",
            "audio_base64": "Zm9vYmFyYmF6YmF6YmF6YmF6YmF6YmF6",
            "mime_type": "audio/webm",
            "target_mode": "orchestrator",
            "dispatch_to_agents": True,
            "preferred_stt_provider": "openai",
            "preferred_tts_provider": "openai",
        },
        actor="pytest-user",
    )

    assert observed_stt_preferences == ["openai"]
    assert spawned == [(sid, "provider aware transcript", "orchestrator", "openai", "balanced")]


def test_resolve_target_agents_uses_mentions_when_present() -> None:
    """@mentions should constrain roster and clean prompt text."""

    roster, cleaned = realtime_ballroom._resolve_target_agents(
        "Need help @Orchestrator and @Scout on this issue",
        ["Orchestrator", "Scout", "Queen"],
    )
    assert roster == ["Orchestrator", "Scout"]
    assert "@Orchestrator" not in cleaned
    assert "@Scout" not in cleaned


def test_resolve_target_agents_falls_back_to_full_roster_when_no_match() -> None:
    """Unknown mentions should not break roster selection."""

    roster, cleaned = realtime_ballroom._resolve_target_agents(
        "Please check this @Unknown",
        ["Orchestrator", "Scout", "Queen"],
    )
    assert roster == ["Orchestrator", "Scout", "Queen"]
    assert "Please check this" in cleaned
