"""Unit tests for Week-1 swarm readiness backend skills."""

from __future__ import annotations

from pathlib import Path

from app.application.services.supervisor.skills import SkillLibrary

WEEK1_SLUGS = [
    "operator-approval-gate",
    "research-to-pr-proposal",
    "marketing-campaign-playbook",
    "trading-paper-discipline",
    "multi-tenant-content-calendar",
    "competitor-scrape-analyze",
    "eshop-ops-research",
    "real-money-risk-gate",
    "social-simulate-first",
    "skill-authoring-template",
]


def test_week1_skills_exist_and_load_when_production_dir_then_all_parse() -> None:
    """All Week-1 skills exist in backend/app/skills and parse with body."""

    skills_dir = Path(__file__).resolve().parents[1] / "app" / "skills"
    lib = SkillLibrary(skills_dir=skills_dir)
    for slug in WEEK1_SLUGS:
        skill = lib.load(slug)
        assert skill is not None, slug
        assert skill.slug == slug
        assert len(skill.body) > 80, slug


def test_week1_skills_select_for_marketing_goal_when_researcher_then_matches_playbook() -> None:
    """Marketing goal selects campaign-related skills for researcher role."""

    lib = SkillLibrary()
    picked = lib.select_for_task(
        role="researcher",
        goal="Run multi-firm marketing campaign competitor scrape",
        max_skills=5,
    )
    assert "marketing-campaign-playbook" in picked or "competitor-scrape-analyze" in picked


def test_week1_skills_select_for_trading_goal_when_critic_then_risk_gate_ranked() -> None:
    """Trading live goal surfaces risk gate skills for critic role."""

    lib = SkillLibrary()
    picked = lib.select_for_task(
        role="critic",
        goal="Approve live real money trading order risk",
        max_skills=5,
    )
    assert "real-money-risk-gate" in picked or "operator-approval-gate" in picked


def test_orchestrator_defaults_include_approval_gate_when_resolved_then_present() -> None:
    """Orchestrator role defaults include operator approval gate."""

    lib = SkillLibrary()
    slugs = lib.resolve_slugs(role="orchestrator")
    assert "operator-approval-gate" in slugs
