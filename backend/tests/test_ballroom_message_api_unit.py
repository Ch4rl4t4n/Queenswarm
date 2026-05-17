"""REST acceptance for Ballroom operator chat ingestion."""

from __future__ import annotations

import asyncio
import uuid

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
async def test_ballroom_voice_transcribe_dispatches_transcript(monkeypatch: pytest.MonkeyPatch, ballroom_auth_fixture: None) -> None:
    """Voice STT endpoint appends user transcript and can dispatch the agent reply loop."""

    sid = uuid.uuid4()
    dispatched: list[tuple[uuid.UUID, str]] = []

    class _FakeResult:
        text = "voice hello"
        provider = "pytest"
        language = "sk"

    async def _ok_transcribe(**_: object) -> _FakeResult:
        return _FakeResult()

    def _record_dispatch(session_id: uuid.UUID, text: str) -> None:
        dispatched.append((session_id, text))

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
    assert dispatched == [(sid, "voice hello")]


@pytest.mark.asyncio
async def test_ballroom_voice_synthesize_returns_audio(monkeypatch: pytest.MonkeyPatch, ballroom_auth_fixture: None) -> None:
    """Voice TTS endpoint proxies synthesized audio bytes as base64 payload."""

    class _S:
        provider = "pytest-tts"
        content_type = "audio/mpeg"
        audio_base64 = "dGVzdA=="

    async def _fake_synthesize(*, text: str) -> _S:
        assert text == "Ahoj swarm"
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
