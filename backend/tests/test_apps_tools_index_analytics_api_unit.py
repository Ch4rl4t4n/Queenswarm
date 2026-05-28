"""ASGI smoke tests for Apps & Tools analytics preference endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    """Reset FastAPI dependency overrides between test cases."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_persists_values(restore_overrides: None) -> None:
    """PATCH endpoint stores tenant-scoped analytics window and compact mode."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"window": "7d", "compact_mode": True},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["window"] == "7d"
    assert body["compact_mode"] is True
    prefs = tenant.operator_settings["apps_tools_index_analytics"]["preferences"]
    assert prefs["window"] == "7d"
    assert prefs["compact_mode"] is True


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_rejects_missing_tenant_context(
    restore_overrides: None,
) -> None:
    """PATCH endpoint returns 403 when tenant context is missing."""

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(get=lambda *_args, **_kwargs: None, commit=lambda: None)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": None,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"window": "24h"},
        )

    assert res.status_code == 403
    assert res.json()["detail"] == "Tenant context missing."


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_returns_404_when_tenant_missing(
    restore_overrides: None,
) -> None:
    """PATCH endpoint returns 404 when tenant row is not found."""

    tenant_id = uuid.uuid4()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, _key: object) -> object | None:
            return None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"compact_mode": True},
        )

    assert res.status_code == 404
    assert res.json()["detail"] == "Tenant not found."


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_rejects_invalid_window(
    restore_overrides: None,
) -> None:
    """PATCH endpoint rejects unsupported window values with validation error."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"window": "30d"},
        )

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_apps_tools_analytics_get_uses_persisted_window_when_query_omitted(
    restore_overrides: None,
) -> None:
    """GET analytics uses stored tenant preference when window query is omitted."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "apps_tools_index_analytics": {
                "preferences": {"window": "7d", "compact_mode": True},
                "events": [],
            }
        },
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        yield SimpleNamespace(get=_get)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/operator/apps-tools-index/analytics",
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["window"] == "7d"
    assert body["compact_mode"] is True


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_window_only_preserves_compact_mode(
    restore_overrides: None,
) -> None:
    """Window-only patch keeps previously persisted compact preference."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "apps_tools_index_analytics": {"preferences": {"window": "24h", "compact_mode": True}}
        },
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"window": "7d"},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["window"] == "7d"
    assert body["compact_mode"] is True


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_compact_only_preserves_window(
    restore_overrides: None,
) -> None:
    """Compact-only patch keeps previously persisted window preference."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "apps_tools_index_analytics": {"preferences": {"window": "7d", "compact_mode": False}}
        },
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"compact_mode": True},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["window"] == "7d"
    assert body["compact_mode"] is True


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_window_null_preserves_existing_window(
    restore_overrides: None,
) -> None:
    """Null window patch keeps previously persisted window value unchanged."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "apps_tools_index_analytics": {"preferences": {"window": "7d", "compact_mode": False}}
        },
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"window": None},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["window"] == "7d"
    assert body["compact_mode"] is False


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_rejects_compact_mode_string(
    restore_overrides: None,
) -> None:
    """PATCH endpoint rejects non-boolean compact_mode payload values."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"compact_mode": "true"},
        )

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_rejects_compact_mode_numeric_with_detail_shape(
    restore_overrides: None,
) -> None:
    """PATCH endpoint rejects numeric compact_mode and keeps validation detail contract."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"compact_mode": 1},
        )

    assert res.status_code == 422
    detail = res.json().get("detail")
    assert isinstance(detail, list)
    assert detail
    first = detail[0]
    assert isinstance(first, dict)
    assert "loc" in first
    assert "msg" in first


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_snapshot_retry(restore_overrides: None) -> None:
    """POST events accepts MCP Ops retry telemetry and persists counter."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_snapshot_retry",
                "module_key": "mcp_ops_studio",
                "source": "mcp_ops_studio_retry",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_snapshot_retry:mcp_ops_studio"] == 1


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_rejects_compact_mode_float_with_detail_shape(
    restore_overrides: None,
) -> None:
    """PATCH endpoint rejects float compact_mode and preserves 422 detail payload contract."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            json={"compact_mode": 1.5},
        )

    assert res.status_code == 422
    detail = res.json().get("detail")
    assert isinstance(detail, list)
    assert detail
    first = detail[0]
    assert isinstance(first, dict)
    assert "loc" in first
    assert "msg" in first


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("json_payload", "raw_content"),
    [
        ({"window": ["7d"]}, None),
        ({"window": {"value": "7d"}}, None),
        ({"window": ""}, None),
        ({"window": "   "}, None),
        ({"window": 24}, None),
        ({"window": True}, None),
        ({"window": 7.5}, None),
        (None, '{"window":1e3}'),
        ({"window": -24}, None),
        ({"window": "24"}, None),
        ({"window": "ALL"}, None),
        ({"window": "AlL"}, None),
    ],
    ids=[
        "array",
        "object",
        "empty-string",
        "whitespace-string",
        "numeric",
        "boolean",
        "decimal",
        "scientific-notation",
        "negative-numeric",
        "string-numeric",
        "uppercase-string",
        "mixed-case-string",
    ],
)
async def test_apps_tools_analytics_preferences_patch_rejects_malformed_window_payloads_with_detail_shape(
    restore_overrides: None,
    json_payload: object | None,
    raw_content: str | None,
) -> None:
    """PATCH endpoint rejects malformed window payload variants and keeps 422 detail shape stable."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        if json_payload is not None:
            res = await client.patch(
                "/api/v1/operator/apps-tools-index/analytics/preferences",
                headers={"Authorization": "Bearer x"},
                json=json_payload,
            )
        else:
            res = await client.patch(
                "/api/v1/operator/apps-tools-index/analytics/preferences",
                headers={"Authorization": "Bearer x", "Content-Type": "application/json"},
                content=raw_content,
            )

    assert res.status_code == 422
    detail = res.json().get("detail")
    assert isinstance(detail, list)
    assert detail
    first = detail[0]
    assert isinstance(first, dict)
    assert "loc" in first
    assert "msg" in first


@pytest.mark.asyncio
async def test_apps_tools_analytics_preferences_patch_rejects_non_object_payload(
    restore_overrides: None,
) -> None:
    """PATCH endpoint rejects primitive JSON payloads from proxy edge."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/operator/apps-tools-index/analytics/preferences",
            headers={"Authorization": "Bearer x"},
            content="true",
        )

    assert res.status_code == 422
    detail = res.json().get("detail")
    assert isinstance(detail, list)
    assert detail
    first = detail[0]
    assert isinstance(first, dict)
    assert "loc" in first
    assert "msg" in first


@pytest.mark.asyncio
async def test_apps_tools_analytics_get_sanitizes_malformed_retry_counters(
    restore_overrides: None,
) -> None:
    """GET analytics payload clamps/filters malformed MCP retry counters."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_snapshot_retry:mcp_ops_studio": -2,
                    "mcp_ops_snapshot_retry:content_factory": "NaN",
                    "mcp_ops_snapshot_retry:research_workspace": "5",
                    "mcp_ops_retry_anomaly_ack:mcp_ops_studio": -1,
                    "mcp_ops_retry_anomaly_ack:content_factory": "NaN",
                    "mcp_ops_retry_anomaly_ack:research_workspace": "2",
                    "mcp_ops_retry_anomaly_ack_reset:mcp_ops_studio": -7,
                    "mcp_ops_retry_anomaly_ack_reset:content_factory": "NaN",
                    "mcp_ops_retry_anomaly_ack_reset:research_workspace": "1",
                    "mcp_ops_lifecycle_recommendation_open:mcp_ops_studio": -6,
                    "mcp_ops_lifecycle_recommendation_open:content_factory": "NaN",
                    "mcp_ops_lifecycle_recommendation_open:research_workspace": "3",
                    "mcp_ops_lifecycle_recommendation_cooldown_block:mcp_ops_studio": -4,
                    "mcp_ops_lifecycle_recommendation_cooldown_block:content_factory": "NaN",
                    "mcp_ops_lifecycle_recommendation_cooldown_block:research_workspace": "2",
                    "mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio": -8,
                    "mcp_ops_lifecycle_recommendation_cooldown_override:content_factory": "NaN",
                    "mcp_ops_lifecycle_recommendation_cooldown_override:research_workspace": "1",
                }
            }
        },
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        yield SimpleNamespace(get=_get)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/operator/apps-tools-index/analytics?window=all",
            headers={"Authorization": "Bearer x"},
        )

    assert res.status_code == 200
    payload = res.json()
    counters = payload["counters"]
    assert counters["mcp_ops_snapshot_retry:mcp_ops_studio"] == 0
    assert counters["mcp_ops_snapshot_retry:research_workspace"] == 5
    assert "mcp_ops_snapshot_retry:content_factory" not in counters
    assert counters["mcp_ops_retry_anomaly_ack:mcp_ops_studio"] == 0
    assert counters["mcp_ops_retry_anomaly_ack:research_workspace"] == 2
    assert "mcp_ops_retry_anomaly_ack:content_factory" not in counters
    assert counters["mcp_ops_retry_anomaly_ack_reset:mcp_ops_studio"] == 0
    assert counters["mcp_ops_retry_anomaly_ack_reset:research_workspace"] == 1
    assert "mcp_ops_retry_anomaly_ack_reset:content_factory" not in counters
    assert counters["mcp_ops_lifecycle_recommendation_open:mcp_ops_studio"] == 0
    assert counters["mcp_ops_lifecycle_recommendation_open:research_workspace"] == 3
    assert "mcp_ops_lifecycle_recommendation_open:content_factory" not in counters
    assert counters["mcp_ops_lifecycle_recommendation_cooldown_block:mcp_ops_studio"] == 0
    assert counters["mcp_ops_lifecycle_recommendation_cooldown_block:research_workspace"] == 2
    assert "mcp_ops_lifecycle_recommendation_cooldown_block:content_factory" not in counters
    assert counters["mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio"] == 0
    assert counters["mcp_ops_lifecycle_recommendation_cooldown_override:research_workspace"] == 1
    assert "mcp_ops_lifecycle_recommendation_cooldown_override:content_factory" not in counters


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_retry_anomaly_ack(
    restore_overrides: None,
) -> None:
    """POST events accepts MCP retry anomaly acknowledgment telemetry."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_retry_anomaly_ack",
                "module_key": "mcp_ops_studio",
                "source": "analytics_retry_strip",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_retry_anomaly_ack:mcp_ops_studio"] == 1


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_retry_anomaly_resurfaced(
    restore_overrides: None,
) -> None:
    """POST events accepts MCP retry anomaly resurfaced telemetry."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_retry_anomaly_resurfaced",
                "module_key": "mcp_ops_studio",
                "source": "analytics_retry_strip",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_retry_anomaly_resurfaced:mcp_ops_studio"] == 1


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_retry_anomaly_ack_reset(
    restore_overrides: None,
) -> None:
    """POST events accepts MCP retry anomaly quick-reset telemetry."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_retry_anomaly_ack_reset",
                "module_key": "mcp_ops_studio",
                "source": "module_card",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_retry_anomaly_ack_reset:mcp_ops_studio"] == 1


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_lifecycle_recommendation_open(
    restore_overrides: None,
) -> None:
    """POST events accepts lifecycle recommendation engagement telemetry."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_lifecycle_recommendation_open",
                "module_key": "mcp_ops_studio",
                "source": "analytics_recommendation",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_lifecycle_recommendation_open:mcp_ops_studio"] == 1


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_lifecycle_recommendation_cooldown_block(
    restore_overrides: None,
) -> None:
    """POST events accepts lifecycle recommendation cooldown-block telemetry."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_lifecycle_recommendation_cooldown_block",
                "module_key": "mcp_ops_studio",
                "source": "analytics_recommendation",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_lifecycle_recommendation_cooldown_block:mcp_ops_studio"] == 1


@pytest.mark.asyncio
async def test_apps_tools_analytics_event_accepts_mcp_ops_lifecycle_recommendation_cooldown_override(
    restore_overrides: None,
) -> None:
    """POST events accepts lifecycle recommendation cooldown-override telemetry."""

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model: object, key: object) -> object | None:
            return tenant if key == tenant_id else None

        async def _commit() -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": tenant_id,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/operator/apps-tools-index/events",
            headers={"Authorization": "Bearer x"},
            json={
                "event": "mcp_ops_lifecycle_recommendation_cooldown_override",
                "module_key": "mcp_ops_studio",
                "source": "analytics_recommendation",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    counters = tenant.operator_settings["apps_tools_index_analytics"]["counters"]
    assert counters["mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio"] == 1
