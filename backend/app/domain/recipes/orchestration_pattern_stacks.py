"""Orchestration template → agentic pattern stack mappings for Recipe Library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.services.supervisor.pattern_router import ALL_PATTERN_IDS

ORCHESTRATION_TEMPLATE_STACKS: dict[str, list[str]] = {
    "exec_assistant": ["planning", "rag", "reflection", "goal_monitoring"],
    "lead_waterfall": ["parallelization", "tool_use", "human_in_the_loop"],
    "life_os": ["memory_management", "prioritization", "reflection", "planning"],
    "research_swarm": ["rag", "reasoning", "exploration", "reflection"],
    "content_flywheel": ["prompt_chaining", "tool_use", "guardrails", "reflection"],
    "product_mission": ["planning", "tool_use", "guardrails", "learning_adaptation"],
}

ORCHESTRATION_TEMPLATE_LABELS: dict[str, str] = {
    "exec_assistant": "Exec Assistant",
    "lead_waterfall": "Lead Waterfall",
    "life_os": "Life OS",
    "research_swarm": "Research Swarm",
    "content_flywheel": "Content Flywheel",
    "product_mission": "Product Mission",
}

PATTERN_LABELS: dict[str, str] = {
    "prompt_chaining": "Prompt Chaining",
    "routing": "Routing",
    "parallelization": "Parallelization",
    "reflection": "Reflection",
    "tool_use": "Tool Use",
    "planning": "Planning",
    "multi_agent": "Multi-Agent",
    "memory_management": "Memory",
    "learning_adaptation": "Learning",
    "goal_monitoring": "Goal Monitoring",
    "exception_handling": "Exception Handling",
    "human_in_the_loop": "Human-in-the-Loop",
    "rag": "RAG",
    "inter_agent_communication": "Inter-Agent Comms",
    "resource_aware": "Resource-Aware",
    "reasoning": "Reasoning",
    "guardrails": "Guardrails",
    "prioritization": "Prioritization",
    "exploration": "Exploration",
}

_NAME_HINTS: tuple[tuple[str, str], ...] = (
    ("exec assistant", "exec_assistant"),
    ("lead waterfall", "lead_waterfall"),
    ("life os", "life_os"),
    ("research swarm", "research_swarm"),
    ("content flywheel", "content_flywheel"),
    ("product mission", "product_mission"),
    ("revenue swarm", "product_mission"),
)


@dataclass(slots=True)
class RecipePatternMeta:
    """Resolved pattern tags for one recipe row."""

    orchestration_template: str | None
    pattern_tags: list[str]
    pattern_labels: list[str]


def normalize_orchestration_template(raw: str | None) -> str | None:
    """Normalize wizard slug / template id to canonical stack key."""

    if not raw or not str(raw).strip():
        return None
    norm = str(raw).strip().lower().replace("-", "_")
    if norm in ORCHESTRATION_TEMPLATE_STACKS:
        return norm
    return None


def infer_orchestration_template(*, name: str, workflow_template: dict[str, Any] | None) -> str | None:
    """Infer orchestration template id from workflow metadata or recipe name."""

    tmpl = workflow_template or {}
    for key in ("orchestration_template", "swarm_wizard_id", "wizard_template_id"):
        resolved = normalize_orchestration_template(str(tmpl.get(key) or ""))
        if resolved is not None:
            return resolved
    seed_key = str(tmpl.get("seed_key") or "").strip().upper()
    if seed_key == "PRODUCT_MISSION":
        return "product_mission"
    name_lower = (name or "").lower()
    for hint, template_id in _NAME_HINTS:
        if hint in name_lower:
            return template_id
    return None


def resolve_pattern_tags(
    *,
    name: str,
    workflow_template: dict[str, Any] | None,
) -> RecipePatternMeta:
    """Resolve orchestration pattern stack for catalog display and imitation routing."""

    tmpl = dict(workflow_template or {})
    explicit = [str(p) for p in list(tmpl.get("pattern_stack") or []) if str(p) in ALL_PATTERN_IDS]
    if explicit:
        deduped = _dedupe(explicit)
        template_id = infer_orchestration_template(name=name, workflow_template=tmpl)
        return RecipePatternMeta(
            orchestration_template=template_id,
            pattern_tags=deduped,
            pattern_labels=[PATTERN_LABELS.get(pid, pid.replace("_", " ").title()) for pid in deduped],
        )

    template_id = infer_orchestration_template(name=name, workflow_template=tmpl)
    if template_id is not None:
        stack = list(ORCHESTRATION_TEMPLATE_STACKS.get(template_id, []))
        return RecipePatternMeta(
            orchestration_template=template_id,
            pattern_tags=stack,
            pattern_labels=[PATTERN_LABELS.get(pid, pid.replace("_", " ").title()) for pid in stack],
        )

    agentic = tmpl.get("agentic_patterns")
    if isinstance(agentic, dict):
        merged = [str(p) for p in list(agentic.get("all") or []) if str(p) in ALL_PATTERN_IDS]
        if not merged:
            merged = [
                str(p)
                for p in [*list(agentic.get("primary") or []), *list(agentic.get("secondary") or [])]
                if str(p) in ALL_PATTERN_IDS
            ]
        deduped = _dedupe(merged)
        if deduped:
            return RecipePatternMeta(
                orchestration_template=template_id,
                pattern_tags=deduped,
                pattern_labels=[PATTERN_LABELS.get(pid, pid.replace("_", " ").title()) for pid in deduped],
            )

    return RecipePatternMeta(orchestration_template=template_id, pattern_tags=[], pattern_labels=[])


def enrich_workflow_template_patterns(template: dict[str, Any]) -> dict[str, Any]:
    """Inject ``pattern_stack`` + ``orchestration_template`` when missing on write."""

    out = dict(template)
    if out.get("pattern_stack"):
        return out
    template_id = infer_orchestration_template(name="", workflow_template=out)
    if template_id is None:
        return out
    out["orchestration_template"] = template_id
    out["pattern_stack"] = list(ORCHESTRATION_TEMPLATE_STACKS.get(template_id, []))
    return out


def list_orchestration_pattern_stacks() -> list[dict[str, Any]]:
    """Return catalog of orchestration templates and their pattern stacks."""

    rows: list[dict[str, Any]] = []
    for template_id, stack in ORCHESTRATION_TEMPLATE_STACKS.items():
        rows.append(
            {
                "id": template_id,
                "label": ORCHESTRATION_TEMPLATE_LABELS.get(template_id, template_id),
                "pattern_tags": stack,
                "pattern_labels": [PATTERN_LABELS.get(pid, pid) for pid in stack],
            },
        )
    return rows


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


__all__ = [
    "ORCHESTRATION_TEMPLATE_STACKS",
    "RecipePatternMeta",
    "enrich_workflow_template_patterns",
    "infer_orchestration_template",
    "list_orchestration_pattern_stacks",
    "resolve_pattern_tags",
]
