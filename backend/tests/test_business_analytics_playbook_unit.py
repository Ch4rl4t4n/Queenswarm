"""Unit tests for Track L DA2 business-analytics-playbook skill."""

from __future__ import annotations

from pathlib import Path

from app.application.services.supervisor.skills import SkillLibrary


def test_business_analytics_playbook_loads_with_frontmatter() -> None:
    skills_dir = Path(__file__).resolve().parents[1] / "app" / "skills"
    lib = SkillLibrary(skills_dir=skills_dir)
    skill = lib.load("business-analytics-playbook")
    assert skill is not None
    assert skill.slug == "business-analytics-playbook"
    assert skill.priority >= 80
    assert "orchestrator" in (skill.roles or [])
    assert "analytics" in (skill.keywords or [])
    assert "Connector order" in skill.body
    assert "Workflow (max 7 steps)" in skill.body


def test_business_analytics_playbook_selects_for_analytics_goal() -> None:
    lib = SkillLibrary()
    picked = lib.select_for_task(
        role="researcher",
        goal="Business analytics report GA4 metrics revenue dashboard decision",
        requested=["business-analytics-playbook"],
        max_skills=6,
    )
    assert "business-analytics-playbook" in picked


def test_orchestrator_defaults_include_business_analytics_playbook() -> None:
    lib = SkillLibrary()
    slugs = lib.resolve_slugs(role="orchestrator")
    assert "business-analytics-playbook" in slugs


def test_business_analytics_report_routine_skills_bundle() -> None:
    from app.application.services.virtual_company_swarm_builder import SWARM_WIZARD_SPECS

    spec = SWARM_WIZARD_SPECS["business-analytics-report"]
    assert "business-analytics-playbook" in spec.routine_skills
    assert "ga4-analytics-playbook" in spec.routine_skills
    assert "self-review-loop" in spec.routine_skills
