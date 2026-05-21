"""Phase 3 Communication & Knowledge connectors — catalog, HTTP surfaces, Obsidian bridge."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.presentation.api.deps import get_db, require_dashboard_session
from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorCreateBody, DynamicConnectorPublic
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService, manifest_unused_query_params
from app.infrastructure.connectors.phase3.catalog import PHASE3_TEMPLATE_INDEX, get_phase3_template, phase3_template_public_dict
from app.infrastructure.connectors.phase3.obsidian_sync import run_obsidian_vault_sync_once
from app.core.jwt_tokens import dashboard_access_subject
from app.main import app


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def test_openapi_lists_phase3_connector_paths() -> None:
    """Phase 3 routes remain discoverable for dashboard codegen + probes."""

    paths = app.openapi().get("paths") or {}
    for route in (
        "/api/v1/connectors/phase3/templates",
        "/api/v1/connectors/phase3/integration-overview",
        "/api/v1/connectors/phase3/instantiate",
        "/api/v1/connectors/phase3/obsidian/status",
        "/api/v1/connectors/phase3/obsidian/sync",
        "/api/v1/connectors/phase3/ballroom-calendar-memo",
    ):
        assert route in paths


def test_phase3_catalog_contains_core_vendors() -> None:
    """Curated templates cover email, calendar, SCM, chat, knowledge, billing."""

    ids = set(PHASE3_TEMPLATE_INDEX.keys())
    for needle in (
        "gmail_google_workspace",
        "outlook_microsoft365",
        "google_calendar",
        "github_rest",
        "gitlab_rest",
        "slack_web_api",
        "telegram_bot_api",
        "discord_bot_api",
        "notion_workspace",
        "stripe_billing",
        "venice_mcp",
    ):
        assert needle in ids


def test_phase3_template_public_shape() -> None:
    """Dashboard projections stay JSON-stable."""

    tpl = get_phase3_template("stripe_billing")
    payload = phase3_template_public_dict(tpl)
    assert payload["template_id"] == "stripe_billing"
    assert payload["tool_count"] == len(payload["tools"])
    assert isinstance(payload["tools"], list)


def test_manifest_unused_query_params_maps_get_extras() -> None:
    """Gmail-style paths promote `{user_id}` replacements while passing `q`, `maxResults`."""

    path = "/gmail/v1/users/{user_id}/messages"
    arguments = {"user_id": "me", "q": "is:unread", "maxResults": "10"}
    params = manifest_unused_query_params(path, arguments)
    assert params == {"q": "is:unread", "maxResults": "10"}


@pytest.mark.asyncio
async def test_obsidian_sync_skips_when_watch_disabled_without_force() -> None:
    """Background gate avoids touching Chroma unless operator enables watch."""

    class _Cfg:
        phase3_obsidian_watch_enabled = False

    out = await run_obsidian_vault_sync_once(_Cfg(), force=False)
    assert out.get("skipped") is True


@pytest.mark.asyncio
async def test_obsidian_sync_force_bypasses_watch_gate_but_respects_hive_flags() -> None:
    """Manual `/phase3/obsidian/sync` uses ``force=True`` but still respects HiveMind toggles."""

    class _Cfg:
        phase3_obsidian_watch_enabled = False
        hive_mind_enabled = False
        hive_mind_chroma_enabled = False

    out = await run_obsidian_vault_sync_once(_Cfg(), force=True)
    assert out.get("skipped") is True


@pytest.mark.asyncio
async def test_phase3_templates_list_ok_with_dashboard_override(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": dashboard_access_subject(uuid.uuid4()),
        "typ": "dashboard_access",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/connectors/phase3/templates")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(PHASE3_TEMPLATE_INDEX)
    assert isinstance(body["templates"], list)


@pytest.mark.asyncio
async def test_phase3_ballroom_memo_accepts_markdown(restore_app_overrides: None) -> None:
    async def mock_db() -> AsyncIterator[AsyncMock]:
        sess = AsyncMock()
        sess.scalar = AsyncMock(return_value=None)
        yield sess

    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": dashboard_access_subject(uuid.uuid4()),
        "typ": "dashboard_access",
    }
    app.dependency_overrides[get_db] = mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/connectors/phase3/ballroom-calendar-memo",
            json={"session_id": "ballroom-test", "summary_markdown": "## Decisions\n- Ship Phase 3 connectors."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("accepted") is True
    hints = payload.get("calendar_hints") or {}
    assert hints.get("recommended_slug") == "google_calendar"
    assert "hub_row_present" in hints


@pytest.mark.asyncio
async def test_phase3_instantiate_maps_template(monkeypatch: pytest.MonkeyPatch, restore_app_overrides: None) -> None:
    """Happy-path wiring into DynamicConnectorService without committing real Postgres rows."""

    captured: dict[str, object] = {}

    async def fake_create_row(
        self: DynamicConnectorService,
        session: AsyncMock,
        *,
        dashboard_user_id: uuid.UUID,
        body: object,
    ) -> DynamicConnectorPublic:
        captured["dashboard_user_id"] = dashboard_user_id
        captured["body"] = body
        return DynamicConnectorPublic(
            id=str(uuid.uuid4()),
            slug="gmail_workspace",
            display_name="Gmail · Google Workspace",
            base_url="https://gmail.googleapis.com",
            auth_type="oauth2",
            mcp_manifest={"tools": []},
            allowed_manager_slugs=["execution_operations", "personal_life", "content_creation"],
            is_active=False,
            is_builtin=False,
            builtin_kind=None,
            last_tested_at=None,
        )

    monkeypatch.setattr(DynamicConnectorService, "create_row", fake_create_row)

    uid = uuid.uuid4()

    async def mock_db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": dashboard_access_subject(uid),
        "typ": "dashboard_access",
    }
    app.dependency_overrides[get_db] = mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/connectors/phase3/instantiate",
            json={"template_id": "gmail_google_workspace"},
        )

    assert response.status_code == 200
    assert captured["dashboard_user_id"] == uid

    body = captured["body"]
    assert isinstance(body, DynamicConnectorCreateBody)
    assert body.slug == "gmail_workspace"
    assert body.auth_type == "oauth2"
    assert body.base_url is not None and str(body.base_url).startswith("https://gmail.googleapis.com")
