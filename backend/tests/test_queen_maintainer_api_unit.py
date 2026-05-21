"""API coverage for Queen Maintainer routes."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_user_with_tenant_role, require_subject


@pytest.fixture
def maintainer_auth_fixture() -> Generator[None, None, None]:
    """Tenant-scoped dashboard principal."""

    actor = uuid.uuid4()
    tenant = uuid.uuid4()
    app.dependency_overrides[require_subject] = lambda: f"dash:{actor}"
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant,
        "tenant_role": "owner",
        "permissions": ["settings:view"],
        "user": MagicMock(id=actor),
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_queen_maintainer_tech_health_route(maintainer_auth_fixture: None) -> None:
    """Tech health endpoint returns read-only repository signals."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/queen-maintainer/tech-health")

    assert resp.status_code == 200
    body = resp.json()
    assert "health_score" in body


@pytest.mark.asyncio
async def test_queen_maintainer_github_webhook_rejects_bad_signature() -> None:
    """Webhook ingress should reject invalid HMAC signatures."""

    with patch("app.presentation.api.routers.queen_maintainer.settings") as mock_settings:
        mock_settings.queen_maintainer_github_webhook_secret = "secret"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/queen-maintainer/github-webhook",
                content=b"{}",
                headers={
                    "X-GitHub-Event": "ping",
                    "X-Hub-Signature-256": "sha256=deadbeef",
                },
            )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_queen_maintainer_github_webhook_accepts_valid_ping() -> None:
    """Valid signature on ping event should return without triggering session."""

    secret = "webhook-secret"
    body = json.dumps({"zen": "Keep it logically awesome.", "hook_id": 1}).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    with patch("app.presentation.api.routers.queen_maintainer.settings") as mock_settings:
        mock_settings.queen_maintainer_github_webhook_secret = secret
        with patch(
            "app.presentation.api.routers.queen_maintainer.handle_github_post_merge_webhook",
            new=AsyncMock(return_value={"triggered": False, "reason": "ping"}),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/queen-maintainer/github-webhook",
                    content=body,
                    headers={
                        "X-GitHub-Event": "ping",
                        "X-Hub-Signature-256": f"sha256={digest}",
                    },
                )

    assert resp.status_code == 200
    assert resp.json()["reason"] == "ping"
