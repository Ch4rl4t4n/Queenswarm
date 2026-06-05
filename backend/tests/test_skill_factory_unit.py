"""Skill Factory unit tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.skill_factory_research import _score_opportunity
from app.application.services.skill_factory_service import build_factory_session_goal, slugify_skill_name
from app.application.services.skill_market_intel import _demand_keyword_hits, _normalize_hits


def test_slugify_skill_name() -> None:
    assert slugify_skill_name("Newsletter Growth Loop!") == "newsletter-growth-loop"
    assert slugify_skill_name("   ") == "skill-factory-output"


def test_score_opportunity_composite_in_range() -> None:
    demand, competition, buildability, composite, rationale = _score_opportunity(
        niche="newsletter growth automation",
        hive_hits=3,
        existing_count=1,
        tenant_skill_count=0,
    )
    assert 0.0 <= demand <= 1.0
    assert 0.0 <= competition <= 1.0
    assert 0.0 <= buildability <= 1.0
    assert 0.0 <= composite <= 1.0
    assert "Demand" in rationale


def test_build_factory_session_goal_includes_niche() -> None:
    from types import SimpleNamespace

    opp = SimpleNamespace(
        niche="SEO blog pipeline",
        title="Skill pack: SEO",
        rationale="High demand signal",
    )
    goal = build_factory_session_goal(opportunity=opp, price_cents=1900)
    assert "SEO blog pipeline" in goal
    assert "€19.00" in goal
    assert "PRODUCT_MISSION" in goal
    assert "Critic verdict: APPROVE" in goal


def test_skill_market_intel_demand_keywords() -> None:
    assert _demand_keyword_hits("cursor skill pack for newsletter automation") >= 2


def test_skill_market_intel_deduplicates_hits() -> None:
    rows = _normalize_hits(
        [
            {"id": "a", "document": "cursor skill template"},
            {"id": "a", "document": "cursor skill template duplicate"},
            {"document": "unique n8n workflow"},
        ],
    )
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_start_factory_build_uses_stateless_shared_context(monkeypatch) -> None:
    """SharedContextService is stateless — must not receive AsyncSession."""
    from app.application.services.skill_factory_service import start_factory_build

    opp_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    row = SimpleNamespace(
        id=opp_id,
        tenant_id=tenant_id,
        status="pending",
        niche="newsletter",
        title="Newsletter pack",
        rationale="test",
        suggested_price_eur_cents=1900,
        supervisor_session_id=None,
        source_refs=[],
    )

    from app.infrastructure.persistence.models.tenant import Tenant
    from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM

    tenant_row = SimpleNamespace(operator_settings={})
    session = AsyncMock()

    async def _session_get(model: type, key: uuid.UUID) -> SimpleNamespace | None:
        if model is SkillOpportunityORM:
            return row
        if model is Tenant:
            return tenant_row
        return None

    session.get = AsyncMock(side_effect=_session_get)
    session.flush = AsyncMock()

    create_mock = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.create_supervisor_session",
        create_mock,
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_service.get_skill_factory_policy",
        AsyncMock(return_value=SimpleNamespace(max_builds_per_week=3)),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_research._weekly_build_count",
        AsyncMock(return_value=0),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_service._load_product_mission_workflow",
        AsyncMock(return_value={"seed_key": "PRODUCT_MISSION", "steps": []}),
    )
    monkeypatch.setattr(
        "app.application.services.factory_llm_readiness_service.assert_factory_build_llm_ready",
        AsyncMock(return_value=None),
    )
    from app.application.services.skill_factory_niche_registry import FactoryNicheFingerprints

    monkeypatch.setattr(
        "app.application.services.skill_factory_niche_registry.load_factory_niche_fingerprints",
        AsyncMock(return_value=FactoryNicheFingerprints()),
    )

    result = await start_factory_build(
        session,
        tenant_id=tenant_id,
        opportunity_id=opp_id,
        created_by_subject="test-subject",
    )

    assert result.status == "building"
    create_mock.assert_awaited_once()
    kwargs = create_mock.await_args.kwargs
    assert kwargs["shared_context"] is not None
    assert kwargs["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_reconcile_building_opportunities_marks_session_done(monkeypatch) -> None:
    """Completed supervisor sessions should move building rows to awaiting_forge."""
    from app.application.services.skill_factory_service import reconcile_building_opportunities

    tenant_id = uuid.uuid4()
    opp_id = uuid.uuid4()
    session_id = uuid.uuid4()
    opp = SimpleNamespace(
        id=opp_id,
        status="building",
        supervisor_session_id=session_id,
    )
    sup = SimpleNamespace(id=session_id, status="completed", tenant_id=tenant_id, goal="", context_summary={})

    forge_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.application.services.skill_factory_forge.propose_skill_factory_forge_from_session",
        forge_mock,
    )

    db = AsyncMock()
    db.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [sup]))
    db.flush = AsyncMock()

    status_map, error_map = await reconcile_building_opportunities(db, tenant_id=tenant_id, opportunities=[opp])

    assert opp.status == "awaiting_forge"
    assert status_map[opp_id] == "completed"
    assert error_map == {}
    forge_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_building_opportunities_marks_orphan_building_failed() -> None:
    """Building rows without a supervisor session should become failed with guidance."""
    from app.application.services.skill_factory_service import reconcile_building_opportunities

    tenant_id = uuid.uuid4()
    opp_id = uuid.uuid4()
    opp = SimpleNamespace(
        id=opp_id,
        status="building",
        supervisor_session_id=None,
    )

    db = AsyncMock()
    db.flush = AsyncMock()

    status_map, error_map = await reconcile_building_opportunities(db, tenant_id=tenant_id, opportunities=[opp])

    assert opp.status == "failed"
    assert status_map[opp_id] == "orphan"
    assert "Rebuild" in error_map[opp_id]
    db.flush.assert_awaited_once()


def test_extract_skill_markdown_from_coder_fence() -> None:
    from app.application.services.skill_factory_forge import extract_skill_markdown_from_outputs

    coder = (
        "### 3. Complete SKILL.md\n\n"
        "```yaml\n"
        "---\n"
        "name: newsletter-growth-automation\n"
        "description: Growth skill\n"
        "---\n\n"
        "# Newsletter Growth\n\n"
        "## Steps\n1. Segment\n"
        "```"
    )
    md = extract_skill_markdown_from_outputs(coder_output=coder, critic_output="", goal="Skill Factory test")
    assert "name: newsletter-growth-automation" in md
    assert "Newsletter Growth" in md


def test_skill_factory_opportunity_counts_actionable_includes_failed() -> None:
    from app.application.services.skill_factory_service import SkillFactoryOpportunityCountsOut

    counts = SkillFactoryOpportunityCountsOut(
        pending=0,
        queued=2,
        building=3,
        awaiting_forge=0,
        failed=13,
        completed=1,
        dismissed=0,
        total=19,
        actionable=18,
    )
    assert counts.actionable == 18
    assert counts.failed == 13


def test_is_skill_factory_session_from_raw_goal() -> None:
    from types import SimpleNamespace

    from app.application.services.skill_factory_forge import is_skill_factory_session

    session = SimpleNamespace(
        goal="=== MISSION ===",
        context_summary={"raw_goal": "Skill Factory — produce a GitHub-ready agent skill"},
    )
    assert is_skill_factory_session(session) is True


def test_quality_gate_critic_approve_and_skill_valid() -> None:
    from app.application.services.skill_factory_quality_gate import (
        critic_approved_factory,
        evaluate_factory_outputs,
        validate_skill_markdown,
    )

    skill = (
        "---\n"
        "name: newsletter-growth\n"
        "description: Automate newsletter growth with guardrails\n"
        "---\n\n"
        "# Newsletter Growth\n\n"
        "## When to use\nBefore scaling paid acquisition.\n\n"
        "## Workflow\n"
        "1. Segment audience\n"
        "2. Draft sequence\n"
        "3. Simulate send\n"
    )
    assert critic_approved_factory("Critic verdict: APPROVE — skill-factory-ready") is True
    valid, issues = validate_skill_markdown(skill)
    assert valid is True
    assert issues == []
    result = evaluate_factory_outputs(
        skill_markdown=skill,
        critic_output="Critic verdict: APPROVE",
        coder_output=skill,
    )
    assert result.passed is True


def test_quality_gate_accepts_step_heading_workflow_format() -> None:
    from app.application.services.skill_factory_quality_gate import validate_skill_markdown

    skill = (
        "---\n"
        "name: crypto-sentiment-alerts\n"
        "description: Real-time sentiment alerts with guardrails\n"
        "---\n\n"
        "# Crypto Sentiment Alerts\n\n"
        "## When to use\nUse when monitoring social sentiment for crypto assets.\n\n"
        "## Workflow (3 steps)\n\n"
        "### Step 1: Fetch sentiment data\n"
        "Collect source posts from approved public feeds.\n\n"
        "### Step 2: Score sentiment shifts\n"
        "Classify bullish and bearish language with thresholds.\n\n"
        "### Step 3: Send simulate-first alert\n"
        "Write alert preview before any live notification.\n"
    )

    valid, issues = validate_skill_markdown(skill)

    assert valid is True
    assert "needs_3_plus_workflow_steps" not in issues


def test_quality_gate_rejects_missing_critic_approve() -> None:
    from app.application.services.skill_factory_quality_gate import evaluate_factory_outputs

    skill = (
        "---\nname: x\ndescription: y\n---\n\n# Title\n1. a\n2. b\n3. c\nWhen to use: now\n"
    )
    result = evaluate_factory_outputs(
        skill_markdown=skill,
        critic_output="Needs more work — rejected",
        coder_output=skill,
    )
    assert result.passed is False
    assert "critic_not_approved" in result.issues


def test_quality_gate_passes_valid_skill_when_critic_is_llm_stub() -> None:
    from app.application.services.skill_factory_quality_gate import evaluate_factory_outputs

    skill = (
        "---\nname: newsletter-growth\ndescription: Verified newsletter growth harness for indie hackers\n"
        "level: 1\n---\n\n# Newsletter growth\n\nWhen to use: weekly operator sessions with simulate-first guardrails.\n\n"
        "## Workflow\n\n1. Research niche context with simulate-first guardrails.\n"
        "2. Draft SKILL.md with critic APPROVE gate.\n3. Export harness bundle after quality pass.\n"
    )
    stub_critic = (
        "# critic — Data Report\n"
        "*Generated without LLM API keys — deterministic tool payloads only.*\n"
    )
    result = evaluate_factory_outputs(
        skill_markdown=skill,
        critic_output=stub_critic,
        coder_output=skill,
    )
    assert result.critic_approved is True
    assert result.passed is True
    assert "critic_not_approved" not in result.issues


def test_hive_llm_credentials_ready_includes_openrouter_vault(monkeypatch) -> None:
    from app.application.services import llm_runtime_credentials as creds
    from app.domain.agents.executor import hive_llm_credentials_ready

    monkeypatch.setattr(creds, "provider_effective_grok", lambda: "")
    monkeypatch.setattr(creds, "provider_effective_anthropic", lambda: "")
    monkeypatch.setattr(creds, "provider_effective_openai", lambda: "")
    monkeypatch.setattr(creds, "provider_effective_openrouter", lambda: "sk-or-test-key")
    assert hive_llm_credentials_ready() is True
