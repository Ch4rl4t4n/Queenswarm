"""REST acceptance for Ballroom operator chat ingestion."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import require_subject
from app.api.routers import realtime_ballroom as rb
from app.main import app


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
    assert sid in rb._CAPSULES


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
        cap = rb._CAPSULES.get(sid_uuid)
        transcripts = cap.get("transcript", []) if isinstance(cap, dict) else []
        if any(isinstance(row, dict) and row.get("agent") == "You" for row in transcripts):
            persisted = True
            break
        await asyncio.sleep(0.025)
    assert persisted, "Expected server-side transcript row for operator message."
