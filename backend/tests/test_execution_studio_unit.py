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


def test_infer_risk_tier_financial_stripe() -> None:
    """Stripe slug maps to financial tier."""

    assert infer_risk_tier(connector_slug="stripe_billing", method="GET", tool_name="list_invoices") == "financial"


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
    assert policy["codebase_pr_only"] is True


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
