"""API coverage for overnight voice report route."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import (
    require_dashboard_session,
    require_dashboard_user_with_tenant_role,
    require_subject,
)
from app.presentation.api.routers import dump_sleep as dump_sleep_router


@pytest.fixture
def overnight_voice_auth_fixture() -> Generator[None, None, None]:
    """Tenant-scoped dashboard principal with dump_sleep + voice features."""

    actor = uuid.uuid4()
    tenant = uuid.uuid4()
    app.dependency_overrides[require_subject] = lambda: f"dash:{actor}"
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{actor}"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant,
        "tenant_role": "owner",
        "permissions": ["connectors:view"],
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_overnight_voice_report_route(
    monkeypatch: pytest.MonkeyPatch,
    overnight_voice_auth_fixture: None,
) -> None:
    """Voice endpoint returns synthesized briefing payload."""

    async def _fake_enabled(*_args: object, **_kwargs: object) -> uuid.UUID:
        return uuid.uuid4()

    async def _fake_payload(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "available": True,
            "batch_id": str(uuid.uuid4()),
            "script_text": "Good morning.",
            "audio_base64": "audio",
            "content_type": "audio/mpeg",
            "provider": "openai",
            "window_hours": 24,
            "voice_disabled": False,
        }

    monkeypatch.setattr(dump_sleep_router, "_assert_overnight_voice_enabled", _fake_enabled)
    monkeypatch.setattr(dump_sleep_router, "build_overnight_voice_payload", _fake_payload)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/dump-sleep/overnight-report/voice")

    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["audio_base64"] == "audio"
