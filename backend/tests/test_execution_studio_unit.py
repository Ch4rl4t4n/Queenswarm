"""Unit tests for Execution Studio service."""

from __future__ import annotations

import uuid

import pytest

from app.application.services.execution_studio import (
    infer_risk_tier,
    merge_studio_policy_patch,
    studio_policy,
)


def test_infer_risk_tier_read_get() -> None:
    """GET tools classify as read risk."""

    assert infer_risk_tier(connector_slug="notion_workspace", method="GET", tool_name="search_pages") == "read"


def test_infer_risk_tier_publish_post() -> None:
    """POST publish-like tools classify as publish."""

    assert (
        infer_risk_tier(connector_slug="slack_web_api", method="POST", tool_name="post_message")
        == "publish"
    )


def test_infer_risk_tier_financial_billing_slug() -> None:
    """Billing slugs map to financial tier."""

    assert infer_risk_tier(connector_slug="billing_provider", method="GET", tool_name="list_invoices") == "financial"


def test_studio_policy_defaults() -> None:
    """Default policy prefers simulate with live approval."""

    policy = studio_policy(None)
    assert policy["default_mode"] == "simulate"
    assert policy["live_requires_approval"] is True


def test_merge_studio_policy_patch() -> None:
    """Patch merges into operator_settings root."""

    merged = merge_studio_policy_patch({}, {"default_mode": "live", "live_requires_approval": False})
    assert merged["execution_studio"]["default_mode"] == "live"
    assert merged["execution_studio"]["live_requires_approval"] is False


@pytest.mark.asyncio
async def test_execute_studio_tool_draft_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Draft mode never calls invoke_dynamic_tool."""

    from app.application.services import execution_studio as mod

    async def _fail_invoke(*_args: object, **_kwargs: object) -> str:
        raise AssertionError("invoke should not run in draft mode")

    monkeypatch.setattr(mod, "invoke_dynamic_tool", _fail_invoke)

    class _Row:
        is_active = True
        mcp_manifest = {"tools": [{"name": "ping", "method": "GET", "path": "/"}]}
        auth_type = "none"
        dashboard_user_id = uuid.uuid4()
        slug = "demo"

    class _Svc:
        async def fetch_by_slug(self, *_a: object, **_k: object) -> _Row:
            return _Row()

        def _secrets_dict(self, _row: object) -> dict[str, str]:
            return {}

    monkeypatch.setattr(mod, "DynamicConnectorService", lambda: _Svc())
    async def _noop_hydrate(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(mod, "hydrate_connector_secrets_from_vault", _noop_hydrate)

    out = await mod.execute_studio_tool(
        None,  # type: ignore[arg-type]
        dashboard_user_id=uuid.uuid4(),
        tenant=None,
        connector_slug="demo",
        tool_name="ping",
        arguments={},
        mode="draft",
    )
    assert out["ok"] is True
    assert out["executed"] is False
    assert out["mode"] == "draft"


def test_studio_policy_codebase_defaults() -> None:
    """Codebase policy fields have safe defaults."""

    policy = studio_policy(None)
    assert policy["codebase_default_mode"] == "simulate"
    assert policy["live_codebase_requires_approval"] is True
    assert policy["codebase_auto_approve_enabled"] is False
    assert policy["codebase_pr_only"] is True


def test_merge_studio_policy_codebase_auto_approve() -> None:
    """Tenant can enable SCV proposal auto-approve."""

    merged = merge_studio_policy_patch({}, {"codebase_auto_approve_enabled": True})
    assert merged["execution_studio"]["codebase_auto_approve_enabled"] is True


@pytest.mark.asyncio
async def test_maybe_auto_approve_codebase_pending_when_policy_off_then_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-approve drain skips tenants without SCV auto-approve policy."""

    from types import SimpleNamespace

    from app.application.services.execution_studio_handoff import maybe_auto_approve_codebase_pending

    async def _fail(*_a: object, **_k: object) -> dict[str, object]:
        raise AssertionError("should not drain")

    monkeypatch.setattr(
        "app.application.services.execution_studio_handoff.auto_approve_pending_codebase_proposals",
        _fail,
    )
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await maybe_auto_approve_codebase_pending(None, tenant=tenant)  # type: ignore[arg-type]
    assert out["processed"] == 0
    assert out["drained"] is False


@pytest.mark.asyncio
async def test_maybe_auto_approve_codebase_pending_when_policy_on_then_drains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auto-approve drain runs when tenant policy enables SCV auto-approve."""

    from types import SimpleNamespace

    from app.application.services.execution_studio_handoff import maybe_auto_approve_codebase_pending

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={"execution_studio": {"codebase_auto_approve_enabled": True}},
    )

    async def _drain(*_a: object, **kwargs: object) -> dict[str, object]:
        assert kwargs.get("tenant_id") == tenant_id
        return {"processed": 3, "skipped": 0, "errors": []}

    monkeypatch.setattr(
        "app.application.services.execution_studio_handoff.auto_approve_pending_codebase_proposals",
        _drain,
    )

    class _Session:
        async def flush(self) -> None:
            return None

    out = await maybe_auto_approve_codebase_pending(_Session(), tenant=tenant)  # type: ignore[arg-type]
    assert out["processed"] == 3
    assert out["drained"] is True


@pytest.mark.asyncio
async def test_submit_codebase_pr_draft_denylist() -> None:
    """Denylist blocks forbidden paths before any GitHub call."""

    from app.application.services.execution_studio import submit_codebase_pr_draft

    out = await submit_codebase_pr_draft(
        None,  # type: ignore[arg-type]
        tenant=None,
        title="Test PR",
        body="Body " * 3,
        slug="test-fix",
        changed_paths=[".env.prod"],
        mode="live",
        operator_confirmed=True,
    )
    assert out["ok"] is False
    assert out["error"] == "denylist_blocked"


@pytest.mark.asyncio
async def test_submit_codebase_pr_draft_simulate() -> None:
    """Simulate mode validates without GitHub invoke."""

    from app.application.services.execution_studio import submit_codebase_pr_draft

    out = await submit_codebase_pr_draft(
        None,  # type: ignore[arg-type]
        tenant=None,
        title="Refactor panel",
        body="Minimal safe diff for execution studio panel.",
        slug="studio-ui",
        changed_paths=["frontend/components/connectors/execution-studio-panel.tsx"],
        mode="simulate",
    )
    assert out["ok"] is True
    assert out["executed"] is False
    assert out["mode"] == "simulate"
