"""API unit tests for operator voice provider preferences."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session


@pytest.fixture
def restore_app_overrides() -> None:
    """Ensure dependency overrides are reset after each test."""

    yield
    app.dependency_overrides.clear()


class _FakeSession:
    """Minimal async DB session for voice preference route tests."""

    def __init__(self, user: DashboardUser) -> None:
        self._user = user
        self.commits = 0
        self.rollbacks = 0

    async def get(self, _model: object, identity: uuid.UUID) -> DashboardUser | None:
        return self._user if identity == self._user.id else None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def _make_user() -> DashboardUser:
    """Build an active admin dashboard user for endpoint authorization."""

    return DashboardUser(
        id=uuid.uuid4(),
        email="voice-admin@queenswarm.love",
        password_hash="hash",
        display_name="Voice Admin",
        timezone=None,
        notification_prefs={},
        totp_secret=None,
        totp_verified_at=None,
        totp_required=False,
        is_admin=True,
        is_active=True,
    )


def _override_auth_and_db(user: DashboardUser, fake_db: _FakeSession) -> None:
    """Attach FastAPI dependency overrides for auth and DB access."""

    async def mock_db() -> AsyncIterator[_FakeSession]:
        yield fake_db

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": f"dash:{user.id}",
        "typ": "dashboard_access",
        "scope": "dash:read dash:operator",
    }


@pytest.mark.asyncio
async def test_voice_preferences_get_defaults_when_unset(restore_app_overrides: None) -> None:
    """GET endpoint returns defaults when user has no stored voice preference."""

    user = _make_user()
    fake_db = _FakeSession(user)
    _override_auth_and_db(user, fake_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/llm-keys/voice-preferences")

    assert response.status_code == 200
    assert response.json() == {
        "stt_provider": "auto",
        "tts_provider": "auto",
        "latency_mode": "fast",
        "vad_threshold": 0.35,
        "silence_duration_ms": 450,
        "tts_voice_id": "eve",
        "tts_language": "auto",
        "tts_tone": "none",
    }


@pytest.mark.asyncio
async def test_voice_preferences_put_persists_user_selection(restore_app_overrides: None) -> None:
    """PUT endpoint stores selected providers in dashboard user notification prefs."""

    user = _make_user()
    fake_db = _FakeSession(user)
    _override_auth_and_db(user, fake_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/llm-keys/voice-preferences",
            json={
                "stt_provider": "deepgram",
                "tts_provider": "openai",
                "latency_mode": "fast",
                "vad_threshold": 0.6,
                "silence_duration_ms": 500,
                "tts_voice_id": "rex",
                "tts_language": "en",
                "tts_tone": "professional",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "stt_provider": "deepgram",
        "tts_provider": "openai",
        "latency_mode": "fast",
        "vad_threshold": 0.6,
        "silence_duration_ms": 500,
        "tts_voice_id": "rex",
        "tts_language": "en",
        "tts_tone": "professional",
    }
    assert fake_db.commits == 1
    assert fake_db.rollbacks == 0
    assert user.notification_prefs == {
        "voice_provider_preferences": {
            "stt_provider": "deepgram",
            "tts_provider": "openai",
            "latency_mode": "fast",
            "vad_threshold": 0.6,
            "silence_duration_ms": 500,
            "tts_voice_id": "rex",
            "tts_language": "en",
            "tts_tone": "professional",
        },
    }


@pytest.mark.asyncio
async def test_voice_preferences_patch_updates_existing_selection(restore_app_overrides: None) -> None:
    """PATCH endpoint updates providers and keeps the same response contract as PUT."""

    user = _make_user()
    user.notification_prefs = {
        "voice_provider_preferences": {
            "stt_provider": "openai",
            "tts_provider": "elevenlabs",
            "latency_mode": "balanced",
        },
    }
    fake_db = _FakeSession(user)
    _override_auth_and_db(user, fake_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/llm-keys/voice-preferences",
            json={"stt_provider": "auto", "tts_provider": "openai", "latency_mode": "fast"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "stt_provider": "auto",
        "tts_provider": "openai",
        "latency_mode": "fast",
        "vad_threshold": 0.35,
        "silence_duration_ms": 450,
        "tts_voice_id": "eve",
        "tts_language": "auto",
        "tts_tone": "none",
    }
    assert fake_db.commits == 1
    assert user.notification_prefs == {
        "voice_provider_preferences": {
            "stt_provider": "auto",
            "tts_provider": "openai",
            "latency_mode": "fast",
            "vad_threshold": 0.35,
            "silence_duration_ms": 450,
            "tts_voice_id": "eve",
            "tts_language": "auto",
            "tts_tone": "none",
        },
    }


@pytest.mark.asyncio
async def test_voice_preferences_accept_grok_as_stt_and_tts(restore_app_overrides: None) -> None:
    """Voice preference schema should allow Grok for both STT and TTS."""

    user = _make_user()
    fake_db = _FakeSession(user)
    _override_auth_and_db(user, fake_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/v1/llm-keys/voice-preferences",
            json={"stt_provider": "grok", "tts_provider": "grok", "latency_mode": "fast"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "stt_provider": "grok",
        "tts_provider": "grok",
        "latency_mode": "fast",
        "vad_threshold": 0.35,
        "silence_duration_ms": 450,
        "tts_voice_id": "eve",
        "tts_language": "auto",
        "tts_tone": "none",
    }
