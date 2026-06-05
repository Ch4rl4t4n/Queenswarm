"""Skill Factory disposition + smart rebuild unit tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.skill_factory_disposition import (
    build_smart_rebuild_goal_appendix,
    derive_niche_from_skill,
    niche_disposition_score_adjustment,
    niche_is_retired,
    resolve_skill_disposition,
    smart_rebuild_from_library_skill,
)
from app.application.services.skill_factory_sellable import SkillSellableAssessment


def test_derive_niche_from_skill_pack_title() -> None:
    skill = SimpleNamespace(
        title="Skill pack: n8n automation templates for agencies",
        slug="n8n-automation-templates-for-agencies-5",
    )
    assert derive_niche_from_skill(skill) == "n8n automation templates for agencies"


def test_niche_is_retired_reads_operator_settings() -> None:
    settings = {
        "skill_factory_dispositions": {
            "by_niche": {"seo blog pipeline": {"disposition": "retired"}},
            "by_slug": {},
        },
    }
    assert niche_is_retired(niche="SEO blog pipeline", settings=settings) is True
    assert niche_is_retired(niche="newsletter growth", settings=settings) is False


def test_niche_disposition_score_adjustment() -> None:
    settings = {
        "skill_factory_dispositions": {
            "by_niche": {
                "cursor packs": {"disposition": "worth_retry"},
                "old niche": {"disposition": "deprioritized"},
            },
            "by_slug": {},
        },
    }
    assert niche_disposition_score_adjustment(niche="cursor packs", settings=settings) == 0.06
    assert niche_disposition_score_adjustment(niche="old niche", settings=settings) == -0.18


def test_build_smart_rebuild_goal_appendix_lists_fixes() -> None:
    skill = SimpleNamespace(
        slug="seo-pipeline-4",
        markdown_body="# SEO\n\n1. Step one\n2. Step two",
    )
    assessment = SkillSellableAssessment(
        tier="rejected",
        score=0.37,
        issues=["critic_not_approved", "needs_3_plus_workflow_steps"],
        recommended_for_launch=False,
    )
    appendix, fix_lines = build_smart_rebuild_goal_appendix(
        skill=skill,
        assessment=assessment,
        attempt_count=2,
    )
    assert "SMART REBUILD" in appendix
    assert "Critic MUST end with" in appendix
    assert len(fix_lines) == 2
    assert "prior slug: seo-pipeline-4" in appendix.lower() or "Prior slug: seo-pipeline-4" in appendix


def test_resolve_skill_disposition_merges_slug_and_niche() -> None:
    settings = {
        "skill_factory_dispositions": {
            "by_slug": {
                "newsletter-growth-3": {
                    "disposition": "worth_retry",
                    "attempt_count": 2,
                    "issues": ["critic_not_approved"],
                },
            },
            "by_niche": {},
        },
    }
    out = resolve_skill_disposition(
        slug="newsletter-growth-3",
        niche="newsletter growth loop",
        settings=settings,
    )
    assert out.disposition == "worth_retry"
    assert out.attempt_count == 2
    assert "critic_not_approved" in out.issues


@pytest.mark.asyncio
async def test_smart_rebuild_from_library_skill_starts_session(monkeypatch) -> None:
    """Smart rebuild creates supervisor session with learnings in goal."""

    tenant_id = uuid.uuid4()
    skill_id = uuid.uuid4()
    opp_id = uuid.uuid4()
    session_id = uuid.uuid4()

    skill = SimpleNamespace(
        id=skill_id,
        tenant_id=tenant_id,
        slug="n8n-templates-5",
        title="Skill pack: n8n automation templates",
        description="draft",
        priority=50,
        markdown_body="# n8n\n\nWorkflow steps here.",
        verified_at=datetime.now(tz=UTC),
    )

    opp = SimpleNamespace(
        id=opp_id,
        tenant_id=tenant_id,
        niche="n8n automation templates",
        title=skill.title,
        rationale="test",
        suggested_price_eur_cents=1900,
        status="queued",
        supervisor_session_id=None,
        source_refs=[],
    )

    tenant = SimpleNamespace(operator_settings={})

    async def fake_get(model, pk):
        if pk == skill_id:
            return skill
        if pk == tenant_id:
            return tenant
        return None

    db = AsyncMock()
    db.get = AsyncMock(side_effect=fake_get)
    db.scalar = AsyncMock(return_value=None)
    db.flush = AsyncMock()

    monkeypatch.setattr(
        "app.application.services.factory_llm_readiness_service.assert_factory_build_llm_ready",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_niche_registry.load_factory_niche_fingerprints",
        AsyncMock(return_value=__import__(
            "app.application.services.skill_factory_niche_registry",
            fromlist=["FactoryNicheFingerprints"],
        ).FactoryNicheFingerprints()),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_disposition._find_or_create_rebuild_opportunity",
        AsyncMock(return_value=opp),
    )
    monkeypatch.setattr(
        "app.application.services.skill_factory_disposition._load_product_mission_workflow",
        AsyncMock(return_value={"steps": [{"id": "s1"}]}),
    )

    sup = SimpleNamespace(id=session_id)

    async def fake_create_supervisor_session(db_session, **kwargs):
        assert kwargs.get("context_seed", {}).get("smart_rebuild") is True
        assert "SMART REBUILD" in str(kwargs.get("goal") or "")
        return sup

    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.create_supervisor_session",
        fake_create_supervisor_session,
    )

    out = await smart_rebuild_from_library_skill(
        db,
        tenant_id=tenant_id,
        skill_id=skill_id,
        created_by_subject="test@example.com",
    )
    assert out.session_id == str(session_id)
    assert out.attempt_count == 1
    assert opp.status == "building"
