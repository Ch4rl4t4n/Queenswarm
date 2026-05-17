"""Map Auto Workflow Breaker previews onto dynamic manager template slugs.

Phase 0.5 keeps heuristics local and testable — orchestrator LLM may still prune the list."""

from __future__ import annotations

from app.domain.agents.managers.registry import MANAGER_REGISTRY, list_manager_slugs
from app.core.config import Settings, get_settings
from app.infrastructure.persistence.models.enums import AgentRole
from app.common.schemas.workflow_breaker import PreviewDecompositionResponse

_ROLE_TO_MANAGER_SLUGS: dict[AgentRole, tuple[str, ...]] = {
    AgentRole.SCRAPER: ("research_intelligence", "execution_operations"),
    AgentRole.LEARNER: ("optimization", "research_intelligence"),
    AgentRole.REPORTER: ("personal_life", "research_intelligence"),
    AgentRole.BLOG_WRITER: ("content_creation",),
    AgentRole.MARKETER: ("content_creation", "optimization"),
    AgentRole.SOCIAL_POSTER: ("content_creation",),
    AgentRole.TRADER: ("execution_operations", "optimization"),
    AgentRole.SIMULATOR: ("review_quality", "execution_operations"),
    AgentRole.EVALUATOR: ("review_quality", "optimization"),
    AgentRole.RECIPE_KEEPER: ("optimization", "review_quality"),
}

_PRIOR_SLUG_RANK: dict[str, int] = {
    slug: idx for idx, slug in enumerate(m.slug for m in MANAGER_REGISTRY)
}


def recipe_tag_for_manager_slug(slug: str) -> str:
    """Namespace tag mirrored into Recipe.topic_tags rows."""

    return f"qs.mt.{slug.strip().lower()}"


def heuristic_manager_slugs(
    preview: PreviewDecompositionResponse | None,
    *,
    specialist_worker_count: int,
    settings: Settings | None = None,
) -> list[str]:
    """Derive deterministic manager lanes from breaker roles + swarm shape."""

    cfg = settings or get_settings()
    cap = max(1, int(cfg.swarm_max_manager_templates_active))

    buckets: dict[str, None] = {}
    ordered: list[str] = []

    def push(slug: str) -> None:
        key = slug.strip().lower()
        if key not in buckets and key in _PRIOR_SLUG_RANK:
            buckets[key] = None
            ordered.append(key)

    if preview is None:
        push("execution_operations")
        return ordered[:cap]

    for row in preview.steps:
        for slug in _ROLE_TO_MANAGER_SLUGS.get(row.agent_role, ()):
            push(slug)

    brief_worker_signal = specialist_worker_count > 0 or any(
        kw in preview.decomposition_rationale.lower()
        for kw in ("worker", "tool", "api", "execute", "integration", "connector")
    )
    if brief_worker_signal:
        push("execution_operations")
    push("review_quality")
    if len(ordered) > cap:
        ordered = sorted(ordered, key=lambda s: _PRIOR_SLUG_RANK.get(s, 99))[:cap]
    else:
        ordered = ordered[:cap]
    return ordered


def ensure_execution_lane(slugs: list[str], *, specialists_available: bool) -> list[str]:
    """Promote Execution & Operations early when tooling is plausible."""

    if not specialists_available:
        return slugs
    trimmed = list(slugs)
    key = "execution_operations"
    if key in trimmed:
        trimmed.remove(key)
    return [key] + trimmed


def cap_template_list(slugs: list[str], settings: Settings | None = None) -> list[str]:
    """Hard cap template breadth for RAM safety on 16GB hosts."""

    cfg = settings or get_settings()
    cap = max(1, int(cfg.swarm_max_manager_templates_active))
    unique: list[str] = []
    seen: set[str] = set()
    for item in slugs:
        ks = item.strip().lower()
        if ks not in seen and ks in _PRIOR_SLUG_RANK:
            seen.add(ks)
            unique.append(ks)
    return unique[:cap]


def parse_orchestrator_template_pick(raw: dict[str, object], fallback: list[str]) -> list[str]:
    """Parse orchestrator JSON with ``template_slugs`` list."""

    picked: list[str] = []
    data = raw.get("template_slugs") or raw.get("manager_templates") or raw.get("slugs") or []
    if isinstance(data, list):
        for item in data:
            slug = str(item).strip().lower()
            picked.append(slug)
    out: list[str] = []
    seen: set[str] = set()
    allowed = list_manager_slugs()
    for slug in picked:
        if slug in allowed and slug not in seen:
            seen.add(slug)
            out.append(slug)
    return out if out else list(fallback)


def describe_template_catalog_compact() -> str:
    """One-line summaries for orch prompts."""

    lines: list[str] = []
    for spec in MANAGER_REGISTRY:
        lines.append(f"- `{spec.slug}` — {spec.display_name}; connectors={list(spec.connector_allowlist)}")
    return "\n".join(lines)


__all__ = [
    "cap_template_list",
    "describe_template_catalog_compact",
    "ensure_execution_lane",
    "heuristic_manager_slugs",
    "parse_orchestrator_template_pick",
    "recipe_tag_for_manager_slug",
]
