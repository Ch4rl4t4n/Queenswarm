"""Rule-based agentic design pattern selection for supervisor sessions.

Maps task signals to proven orchestration patterns (Kashef / industry catalog).
P0: heuristic router — P1: optional LLM refinement hop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Canonical pattern IDs — synced with docs/QUEENSWARM_DESIGN_PATTERNS.md
PATTERN_PROMPT_CHAINING = "prompt_chaining"
PATTERN_ROUTING = "routing"
PATTERN_PARALLELIZATION = "parallelization"
PATTERN_REFLECTION = "reflection"
PATTERN_TOOL_USE = "tool_use"
PATTERN_PLANNING = "planning"
PATTERN_MULTI_AGENT = "multi_agent"
PATTERN_MEMORY = "memory_management"
PATTERN_LEARNING = "learning_adaptation"
PATTERN_GOAL_MONITORING = "goal_monitoring"
PATTERN_EXCEPTION_HANDLING = "exception_handling"
PATTERN_HUMAN_IN_LOOP = "human_in_the_loop"
PATTERN_RAG = "rag"
PATTERN_INTER_AGENT = "inter_agent_communication"
PATTERN_RESOURCE_AWARE = "resource_aware"
PATTERN_REASONING = "reasoning"
PATTERN_GUARDRAILS = "guardrails"
PATTERN_PRIORITIZATION = "prioritization"
PATTERN_EXPLORATION = "exploration"

ALL_PATTERN_IDS: frozenset[str] = frozenset(
    {
        PATTERN_PROMPT_CHAINING,
        PATTERN_ROUTING,
        PATTERN_PARALLELIZATION,
        PATTERN_REFLECTION,
        PATTERN_TOOL_USE,
        PATTERN_PLANNING,
        PATTERN_MULTI_AGENT,
        PATTERN_MEMORY,
        PATTERN_LEARNING,
        PATTERN_GOAL_MONITORING,
        PATTERN_EXCEPTION_HANDLING,
        PATTERN_HUMAN_IN_LOOP,
        PATTERN_RAG,
        PATTERN_INTER_AGENT,
        PATTERN_RESOURCE_AWARE,
        PATTERN_REASONING,
        PATTERN_GUARDRAILS,
        PATTERN_PRIORITIZATION,
        PATTERN_EXPLORATION,
    },
)

_PATTERN_SKILL_HINTS: dict[str, list[str]] = {
    PATTERN_REFLECTION: ["self-review-loop", "meta-reasoning-reflection"],
    PATTERN_PLANNING: ["multi-step-reasoning", "decision-frameworks", "automation-proposal"],
    PATTERN_TOOL_USE: ["tool-use-orchestration", "automation-proposal"],
    PATTERN_RAG: ["context", "swarm-memory-evolution"],
    PATTERN_EXCEPTION_HANDLING: ["diagnose"],
    PATTERN_REASONING: ["multi-step-reasoning", "decision-frameworks"],
    PATTERN_GUARDRAILS: ["self-review-loop", "tdd"],
    PATTERN_LEARNING: ["agent-initiative-proposals"],
    PATTERN_MEMORY: ["swarm-memory-evolution", "context"],
}

_PARALLEL_HINTS = re.compile(
    r"\b(parallel|concurrent|multiple|batch|bulk|many|all\s+at\s+once)\b",
    re.IGNORECASE,
)
_PLANNING_HINTS = re.compile(
    r"\b(plan|roadmap|strategy|multi.?step|workflow|orchestrat|break\s+down|decompos)\b",
    re.IGNORECASE,
)
_RESEARCH_HINTS = re.compile(
    r"\b(research|analyze|investigate|compare|report|summari[sz]e|audit)\b",
    re.IGNORECASE,
)
_UNCLEAR_HINTS = re.compile(
    r"\b(unclear|ambiguous|not\s+sure|figure\s+out|explore|discover)\b",
    re.IGNORECASE,
)
_TOOL_HINTS = re.compile(
    r"\b(scrape|browser|api|integrat|connect|fetch|deploy|build|code|implement)\b",
    re.IGNORECASE,
)
_RISK_HINTS = re.compile(
    r"\b(production|critical|payment|security|compliance|legal|approve)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class PatternSelection:
    """Selected agentic patterns for one supervisor session."""

    primary: list[str] = field(default_factory=list)
    secondary: list[str] = field(default_factory=list)
    forced_reflection: bool = True
    resource_aware: bool = False
    rationale: list[str] = field(default_factory=list)
    router_version: str = "heuristic-v1"

    def all_patterns(self) -> list[str]:
        """Return deduplicated primary + secondary pattern IDs."""

        seen: set[str] = set()
        out: list[str] = []
        for pid in [*self.primary, *self.secondary]:
            if pid not in seen and pid in ALL_PATTERN_IDS:
                seen.add(pid)
                out.append(pid)
        return out

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``context_summary`` and event payloads."""

        return {
            "primary": list(self.primary),
            "secondary": list(self.secondary),
            "all": self.all_patterns(),
            "forced_reflection": self.forced_reflection,
            "resource_aware": self.resource_aware,
            "rationale": list(self.rationale),
            "router_version": self.router_version,
        }


def select_patterns_for_task(
    *,
    goal: str,
    roles: list[str] | None = None,
    forced_reflection: bool = True,
) -> PatternSelection:
    """Analyze goal text and roles; return recommended pattern stack (no LLM call).

    Args:
        goal: Raw supervisor goal text.
        roles: Normalized sub-agent roles for the session.
        forced_reflection: When True, always include reflection pattern + skills.

    Returns:
        PatternSelection with primary/secondary stacks and skill hints.
    """
    text = (goal or "").strip()
    norm_roles = [r.strip().lower().replace("-", "_") for r in (roles or []) if r.strip()]
    role_count = len(norm_roles)
    selection = PatternSelection(forced_reflection=forced_reflection)

    # Baseline — every verified supervisor session
    selection.primary.extend([PATTERN_PLANNING, PATTERN_MULTI_AGENT, PATTERN_RAG, PATTERN_GUARDRAILS])
    selection.rationale.append("baseline: planning + multi-agent + RAG + guardrails")

    if role_count >= 2 or _PARALLEL_HINTS.search(text):
        selection.primary.append(PATTERN_PARALLELIZATION)
        selection.rationale.append("multi-role or parallel keywords → parallelization")

    if _PLANNING_HINTS.search(text):
        selection.primary.append(PATTERN_PROMPT_CHAINING)
        selection.rationale.append("planning keywords → prompt chaining")

    if _RESEARCH_HINTS.search(text):
        selection.secondary.extend([PATTERN_REASONING, PATTERN_MEMORY])
        selection.rationale.append("research keywords → reasoning + memory")

    if _UNCLEAR_HINTS.search(text):
        selection.secondary.extend([PATTERN_EXPLORATION, PATTERN_GOAL_MONITORING])
        selection.rationale.append("ambiguous goal → exploration + goal monitoring")

    if _TOOL_HINTS.search(text) or "browser" in norm_roles or "coder" in norm_roles:
        selection.primary.append(PATTERN_TOOL_USE)
        selection.rationale.append("tool/build keywords or roles → tool use")

    if _RISK_HINTS.search(text):
        selection.primary.append(PATTERN_HUMAN_IN_LOOP)
        selection.rationale.append("risk keywords → human-in-the-loop")

    selection.secondary.extend(
        [
            PATTERN_EXCEPTION_HANDLING,
            PATTERN_LEARNING,
            PATTERN_INTER_AGENT,
            PATTERN_ROUTING,
        ],
    )

    if forced_reflection:
        if PATTERN_REFLECTION not in selection.primary:
            selection.primary.append(PATTERN_REFLECTION)
        selection.rationale.append("forced reflection: critic → revise → validate before output")

    # Resource-aware when goal looks lightweight (short) or explicitly mentions cost
    if len(text) < 120 or re.search(r"\b(cheap|budget|token|cost)\b", text, re.IGNORECASE):
        selection.resource_aware = True
        selection.secondary.append(PATTERN_RESOURCE_AWARE)
        selection.rationale.append("short/cost-sensitive goal → resource-aware routing hint")

    # Deduplicate while preserving order
    selection.primary = _dedupe(selection.primary)
    selection.secondary = _dedupe([p for p in selection.secondary if p not in selection.primary])

    return selection


def pattern_skill_slugs(selection: PatternSelection) -> list[str]:
    """Map selected patterns to Markdown skill slugs for SkillLibrary."""

    slugs: list[str] = []
    seen: set[str] = set()
    for pid in selection.all_patterns():
        for slug in _PATTERN_SKILL_HINTS.get(pid, []):
            if slug not in seen:
                seen.add(slug)
                slugs.append(slug)
    return slugs


def build_pattern_prompt_block(selection: PatternSelection) -> str:
    """Compact prompt appendix describing active patterns for sub-agents."""

    lines = [
        "## Agentic design patterns (Queenswarm Pattern Router)",
        f"Primary: {', '.join(selection.primary) or 'none'}",
        f"Secondary: {', '.join(selection.secondary) or 'none'}",
    ]
    if selection.forced_reflection:
        lines.append(
            "Reflection gate: run Critic → Revise → Validate before marking output verified.",
        )
    if selection.resource_aware:
        lines.append("Resource-aware: prefer economy model hops for simple sub-steps.")
    if selection.rationale:
        lines.append("Rationale: " + "; ".join(selection.rationale[:4]))
    return "\n".join(lines)


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
    "ALL_PATTERN_IDS",
    "PatternSelection",
    "build_pattern_prompt_block",
    "pattern_skill_slugs",
    "select_patterns_for_task",
]
