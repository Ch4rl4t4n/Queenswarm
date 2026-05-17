"""Registry for the six Ballroom manager personas."""

from __future__ import annotations

from app.domain.agents.managers.spec import ManagerTemplateSpec
from app.infrastructure.persistence.models.enums import AgentRole

MANAGER_REGISTRY: tuple[ManagerTemplateSpec, ...] = (
    ManagerTemplateSpec(
        slug="research_intelligence",
        display_name="Research & Intelligence Manager",
        connector_allowlist=(),
        sub_swarm_roles=(
            AgentRole.SCRAPER,
            AgentRole.LEARNER,
            AgentRole.REPORTER,
            AgentRole.SIMULATOR,
        ),
        prompt_rel_path="prompts/research_intelligence.md",
    ),
    ManagerTemplateSpec(
        slug="content_creation",
        display_name="Content & Creation Manager",
        connector_allowlist=(),
        sub_swarm_roles=(
            AgentRole.BLOG_WRITER,
            AgentRole.MARKETER,
            AgentRole.SOCIAL_POSTER,
            AgentRole.REPORTER,
        ),
        prompt_rel_path="prompts/content_creation.md",
    ),
    ManagerTemplateSpec(
        slug="execution_operations",
        display_name="Execution & Operations Manager",
        connector_allowlist=("mcp_placeholder",),
        sub_swarm_roles=(
            AgentRole.TRADER,
            AgentRole.SCRAPER,
            AgentRole.REPORTER,
            AgentRole.SIMULATOR,
        ),
        prompt_rel_path="prompts/execution_operations.md",
    ),
    ManagerTemplateSpec(
        slug="review_quality",
        display_name="Review & Quality Manager",
        connector_allowlist=(),
        sub_swarm_roles=(
            AgentRole.EVALUATOR,
            AgentRole.SIMULATOR,
            AgentRole.LEARNER,
        ),
        prompt_rel_path="prompts/review_quality.md",
    ),
    ManagerTemplateSpec(
        slug="personal_life",
        display_name="Personal & Life Manager",
        connector_allowlist=(),
        sub_swarm_roles=(
            AgentRole.REPORTER,
            AgentRole.LEARNER,
        ),
        prompt_rel_path="prompts/personal_life.md",
    ),
    ManagerTemplateSpec(
        slug="optimization",
        display_name="Optimization Manager",
        connector_allowlist=(),
        sub_swarm_roles=(
            AgentRole.RECIPE_KEEPER,
            AgentRole.LEARNER,
            AgentRole.EVALUATOR,
        ),
        prompt_rel_path="prompts/optimization.md",
    ),
)

_BY_SLUG: dict[str, ManagerTemplateSpec] = {m.slug: m for m in MANAGER_REGISTRY}


def get_manager_template(slug: str) -> ManagerTemplateSpec:
    """Resolve a manager lane by deterministic slug."""

    key = slug.strip().lower()
    if key not in _BY_SLUG:
        msg = f"unknown_manager_template_slug:{slug}"
        raise KeyError(msg)
    return _BY_SLUG[key]


def list_manager_slugs() -> tuple[str, ...]:
    """Stable ordering for orch prompts."""

    return tuple(m.slug for m in MANAGER_REGISTRY)


__all__ = [
    "MANAGER_REGISTRY",
    "get_manager_template",
    "list_manager_slugs",
]
