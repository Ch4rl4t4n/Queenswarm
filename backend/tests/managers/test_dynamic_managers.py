"""Tests for Phase 0.5 dynamic Ballroom manager personas."""

from __future__ import annotations

import pytest

from app.domain.agents.factory import specialist_roles_for_manager_lane
from app.domain.agents.managers import get_manager_template, list_manager_slugs
from app.infrastructure.persistence.models.enums import AgentRole
from app.common.schemas.workflow_breaker import PreviewDecompositionResponse, PreviewWorkflowStep
from app.application.services.swarm_manager_selection import (
    cap_template_list,
    describe_template_catalog_compact,
    ensure_execution_lane,
    heuristic_manager_slugs,
    parse_orchestrator_template_pick,
    recipe_tag_for_manager_slug,
)


class _SwarmCaps:
    """Minimal Settings stand-in for template-capping helpers."""

    swarm_max_manager_templates_active: int = 2


@pytest.fixture()
def swarm_two_cap() -> _SwarmCaps:
    return _SwarmCaps()


def test_list_manager_slugs_has_six_canonical_templates() -> None:
    """Seeded personas remain stable identifiers for Ballroom routing."""

    slugs = list_manager_slugs()
    assert len(slugs) == 6
    assert "execution_operations" in slugs


def test_manager_prompts_load_nonempty() -> None:
    """Every bundled Markdown template must hydrate for runtime prompts."""

    for slug in list_manager_slugs():
        blob = get_manager_template(slug).prompt_text()
        assert len(blob) > 80
        assert slug.replace("_", "")[:4].lower() in blob.lower() or "manager" in blob.lower()


@pytest.mark.parametrize("slug", list(list_manager_slugs()))
def test_specialist_roles_resolve_for_every_lane(slug: str) -> None:
    """Factory exposes sub-swarm role hints sourced from MANAGER_REGISTRY."""

    roles = specialist_roles_for_manager_lane(slug)
    assert 2 <= len(roles) <= 5
    assert all(isinstance(role, AgentRole) for role in roles)


def test_execution_lane_promoted_when_workers_exist() -> None:
    """Workers present → execution template should precede heuristic ordering."""

    ordered = ["review_quality", "optimization"]
    bumped = ensure_execution_lane(ordered, specialists_available=True)
    assert bumped[0] == "execution_operations"


def test_cap_template_list_unique_and_bounded(swarm_two_cap: _SwarmCaps) -> None:
    """RAM guard dedupes and slices unknown slugs deterministically."""

    mixed = ["execution_operations", "unknown_slug", "execution_operations", "review_quality"]
    capped = cap_template_list(mixed, settings=swarm_two_cap)
    assert capped == ["execution_operations", "review_quality"]
    capped_small = cap_template_list(
        [
            "personal_life",
            "research_intelligence",
            "optimization",
            "content_creation",
        ],
        settings=swarm_two_cap,
    )
    assert len(capped_small) == 2


def test_heuristic_orders_from_breaker_roles(swarm_two_cap: _SwarmCaps) -> None:
    """Breaker roles map deterministically onto manager personas."""

    preview = PreviewDecompositionResponse(
        steps=[
            PreviewWorkflowStep(
                step_order=1,
                description="scrape competitor pricing pages",
                agent_role=AgentRole.SCRAPER,
                guardrail_summary="public only",
                guardrails={"public_sources": True},
                evaluation_criteria={"has_citations": True},
            ),
            PreviewWorkflowStep(
                step_order=2,
                description="simulate traffic impact",
                agent_role=AgentRole.SIMULATOR,
                guardrail_summary="synthetic loads",
                guardrails={},
                evaluation_criteria={},
            ),
        ],
        decomposition_rationale="Use external APIs and scraping workers",
        parallel_groups=[[]],
        decomposition_cost_usd=0.0,
    )

    guessed = heuristic_manager_slugs(preview, specialist_worker_count=0, settings=swarm_two_cap)
    assert "research_intelligence" in guessed or "execution_operations" in guessed
    assert len(guessed) <= swarm_two_cap.swarm_max_manager_templates_active


def test_parse_orchestrator_template_pick_filters_unknown() -> None:
    """Orchestrator JSON must ignore junk while preserving deterministic order."""

    raw: dict[str, object] = {
        "template_slugs": ["bad_slug", "content_creation", "review_quality"],
        "rationale": "unit",
    }
    picked = parse_orchestrator_template_pick(raw, fallback=["research_intelligence"])
    assert picked == ["content_creation", "review_quality"]


def test_recipe_tag_namespace() -> None:
    """Topic tags mirror slug namespace."""

    assert recipe_tag_for_manager_slug("execution_operations") == "qs.mt.execution_operations"


def test_compact_catalog_contains_each_slug_line() -> None:
    """Orchestrator prompt helper enumerates personas."""

    blob = describe_template_catalog_compact()
    for slug in list_manager_slugs():
        assert slug in blob
