"""Phase 7 — handoff flow integration, browser step, cost tier."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_browser import execute_browser_fallback_step
from app.application.services.execution_studio_handoff import CODEBASE_PROPOSAL_TYPE
from app.application.services.super_tool_router import (
    connector_cost_tier_for_slug,
    is_connector_cost_allowed,
)


def test_cost_tier_blocks_high_on_medium_cap() -> None:
    """Router max_cost_tier medium blocks high-tier connectors."""

    high_slug = "monid_mcp"
    tier = connector_cost_tier_for_slug(high_slug)
    if tier == "high":
        assert is_connector_cost_allowed(connector_slug=high_slug, max_cost_tier="medium") is False
    assert is_connector_cost_allowed(connector_slug="notion_workspace", max_cost_tier="high") is True


@pytest.mark.asyncio
async def test_browser_step_draft_never_runs_harness(monkeypatch: pytest.MonkeyPatch) -> None:
    """Draft browser step returns preview without BrowserManager."""

    async def _fail_create(*_a: object, **_k: object) -> object:
        raise AssertionError("BrowserManager should not run in draft mode")

    monkeypatch.setattr(
        "app.application.services.execution_studio_browser.BrowserManager.create_session",
        _fail_create,
    )

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await execute_browser_fallback_step(
        None,  # type: ignore[arg-type]
        tenant=tenant,  # type: ignore[arg-type]
        dashboard_user_id=uuid.uuid4(),
        goal="Verify https://queenswarm.love pricing page",
        mode="draft",
    )
    assert out.get("ok") is True
    assert out.get("executed") is False


@pytest.mark.asyncio
async def test_research_proposal_approve_handoff_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Research proposal → approve → Maintainer handoff chain."""

    from app.application.services.execution_studio_handoff import (
        create_codebase_execution_proposal,
        handoff_on_approved_proposal,
    )
    from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})
    handoff_calls: list[str] = []

    async def _fake_maintainer(_session: object, *, tenant: object, created_by_subject: str, proposal: object) -> dict:
        handoff_calls.append(created_by_subject)
        return {"ok": True, "session_id": str(uuid.uuid4())}

    monkeypatch.setattr(
        "app.application.services.execution_studio_handoff.trigger_maintainer_with_proposal_goal",
        _fake_maintainer,
    )

    class _Session:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, row: object) -> None:
            self.added.append(row)

        async def flush(self) -> None:
            for row in self.added:
                if isinstance(row, AgentSuggestion) and row.id is None:
                    row.id = uuid.uuid4()

        async def get(self, _model: type, _key: uuid.UUID) -> SimpleNamespace | None:
            if _key == tenant_id:
                return tenant
            return None

    db = _Session()
    proposal = await create_codebase_execution_proposal(
        db,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        supervisor_session_id=uuid.uuid4(),
        sub_agent_session_id=uuid.uuid4(),
        proposed_by_role="researcher",
        title="Refactor connector refresh",
        description="Dual-write OAuth refresh to hub.",
        goal_excerpt="Implement token refresh dual-write in dynamic hub.",
        source="research_agent",
    )
    assert proposal.proposal_type == CODEBASE_PROPOSAL_TYPE
    proposal.status = "approved"

    result = await handoff_on_approved_proposal(
        db,  # type: ignore[arg-type]
        suggestion=proposal,
        tenant=tenant,  # type: ignore[arg-type]
        reviewer_subject="dashboard:operator",
    )
    assert result is not None
    assert result.get("ok") is True
    assert len(handoff_calls) == 1
