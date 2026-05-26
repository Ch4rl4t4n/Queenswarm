"""Phase 11 — operator_confirmed execute, pending snapshot, time-series telemetry."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_pending import (
    build_pending_approvals_snapshot,
    collect_pending_live_actions,
)
from app.application.services.execution_studio_telemetry import build_activity_telemetry


def test_collect_pending_live_actions_dedupes() -> None:
    """Activity feed pending rows become actionable live confirmations."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "browser_step",
                        "message": "Browser live step pending operator approval",
                        "payload": {"pending_approval": True, "mode": "live"},
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "External live pending approval: slack_workspace/post_message",
                        "payload": {
                            "pending_approval": True,
                            "connector_slug": "slack_workspace",
                            "tool_name": "post_message",
                            "proposal_id": str(uuid.uuid4()),
                        },
                        "at": "2026-05-21T12:01:00+00:00",
                    },
                ],
            },
        },
    )
    actions = collect_pending_live_actions(tenant, limit=40)
    assert len(actions) == 2
    types = {item["type"] for item in actions}
    assert types == {"browser", "external"}


def test_activity_time_series_hourly_buckets() -> None:
    """Telemetry exposes hourly runs/blocks series for charts."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "tool_execute",
                        "message": "Simulated: notion/search",
                        "payload": {},
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "cost_tier_blocked",
                        "payload": {"error": "cost_tier_blocked"},
                        "at": "2026-05-21T12:30:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "Simulated: slack/post",
                        "payload": {},
                        "at": "2026-05-21T13:00:00+00:00",
                    },
                ],
            },
        },
    )
    tel = build_activity_telemetry(tenant, limit=40)
    assert len(tel["activity_time_series"]) == 2
    assert tel["activity_time_series"][0]["runs"] == 2
    assert tel["activity_time_series"][0]["blocks"] == 1
    assert tel["activity_time_series"][1]["runs"] == 1


@pytest.mark.asyncio
async def test_execute_live_requires_operator_confirmed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Live write tools blocked until operator_confirmed=True."""

    from app.application.services import execution_studio as mod

    class _Row:
        is_active = True
        mcp_manifest = {"tools": [{"name": "update_page", "method": "PATCH", "path": "/pages/{id}"}]}
        auth_type = "bearer_token"
        dashboard_user_id = uuid.uuid4()
        slug = "notion_workspace"

    class _Svc:
        async def fetch_by_slug(self, *_a: object, **_k: object) -> _Row:
            return _Row()

        def _secrets_dict(self, _row: object) -> dict[str, str]:
            return {}

    monkeypatch.setattr(mod, "DynamicConnectorService", lambda: _Svc())

    async def _noop_hydrate(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(mod, "hydrate_connector_secrets_from_vault", _noop_hydrate)

    async def _noop_persist(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(mod, "persist_execution_activity", _noop_persist)

    async def _fail_invoke(*_a: object, **_k: object) -> str:
        raise AssertionError("invoke should not run without confirmation")

    monkeypatch.setattr(mod, "invoke_dynamic_tool", _fail_invoke)

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await mod.execute_studio_tool(
        None,  # type: ignore[arg-type]
        dashboard_user_id=uuid.uuid4(),
        tenant=tenant,  # type: ignore[arg-type]
        connector_slug="notion_workspace",
        tool_name="update_page",
        arguments={"page_id": "x"},
        mode="live",
        operator_confirmed=False,
    )
    assert out.get("error") == "approval_required"

    async def _ok_invoke(*_a: object, **_k: object) -> str:
        return '{"ok": true}'

    monkeypatch.setattr(mod, "invoke_dynamic_tool", _ok_invoke)

    out2 = await mod.execute_studio_tool(
        None,  # type: ignore[arg-type]
        dashboard_user_id=uuid.uuid4(),
        tenant=tenant,  # type: ignore[arg-type]
        connector_slug="notion_workspace",
        tool_name="update_page",
        arguments={"page_id": "x"},
        mode="live",
        operator_confirmed=True,
    )
    assert out2.get("ok") is True


@pytest.mark.asyncio
async def test_build_pending_approvals_snapshot_counts_codebase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pending snapshot aggregates live actions and codebase proposals."""

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={"execution_studio": {"recent_activity": []}})

    class _Session:
        pass

    async def _fake_codebase(*_a: object, **_k: object) -> list[object]:
        return [object(), object()]

    monkeypatch.setattr(
        "app.application.services.execution_studio_pending.list_pending_codebase_proposals",
        _fake_codebase,
    )
    snap = await build_pending_approvals_snapshot(_Session(), tenant=tenant)  # type: ignore[arg-type]
    assert snap["codebase_pending"] == 2
    assert snap["count"] == 2
