"""Meta-reasoning and self-reflection helpers for supervisor runtime cycles."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def evaluate_meta_reasoning(
    *,
    role: str,
    goal: str,
    retrieval_sections: list[str],
    selected_skills: list[str],
    issues: list[str],
    alternatives: list[str],
    attempts: int,
    resolved: bool,
) -> dict[str, Any]:
    """Score execution strategy quality and suggest adaptation direction."""

    score = 1.0
    score -= min(0.45, len(issues) * 0.12)
    score -= min(0.25, max(0, attempts - 1) * 0.1)
    if not retrieval_sections:
        score -= 0.15
    if not selected_skills:
        score -= 0.1
    score = max(0.0, min(1.0, score))

    recommended_shift = "maintain_strategy"
    if "missing_context" in issues:
        recommended_shift = "expand_retrieval_contract"
    elif "missing_skills" in issues:
        recommended_shift = "strengthen_skill_stack"
    elif "tool_failure" in issues:
        recommended_shift = "reduce_tool_surface_and_retry"
    elif "bad_output" in issues:
        recommended_shift = "tighten_acceptance_criteria"

    return {
        "role": str(role).strip().lower().replace("-", "_"),
        "goal_excerpt": goal[:220],
        "resolved": bool(resolved),
        "attempts": int(attempts),
        "strategy_score": round(score, 4),
        "retrieval_coverage": len(retrieval_sections),
        "skills_applied": len(selected_skills),
        "issues": list(issues),
        "alternative_count": len(alternatives),
        "recommended_shift": recommended_shift,
        "evaluated_at": datetime.now(tz=UTC).isoformat(),
    }


def build_reflection_cycle(
    *,
    role: str,
    goal: str,
    attempt: int,
    issues: list[str],
    resolved: bool,
    output_preview: str,
    meta_reasoning: dict[str, Any],
) -> dict[str, Any]:
    """Build a compact reflection report with explicit improvement tracks."""

    issue_map = {
        "tool_failure": "Tool execution instability",
        "missing_context": "Insufficient retrieval context",
        "bad_output": "Output quality below acceptance threshold",
        "missing_skills": "Missing relevant skills in prompt stack",
    }
    failures = [issue_map.get(item, item) for item in issues]
    if resolved:
        went_well = [
            "Execution reached a stable output for this step.",
            "Strategy adaptation reduced blockers compared to prior attempts.",
        ]
    else:
        went_well = ["Partial progress recorded with explicit blocker classification."]

    to_improve = [f"Address: {label}" for label in failures] or ["Maintain current strategy and continue monitoring."]
    recommended_shift = str(meta_reasoning.get("recommended_shift") or "maintain_strategy")
    to_improve.append(f"Next strategic adjustment: {recommended_shift}")

    return {
        "role": str(role).strip().lower().replace("-", "_"),
        "goal_excerpt": goal[:220],
        "attempt": int(attempt),
        "resolved": bool(resolved),
        "issues": list(issues),
        "what_went_well": went_well,
        "what_failed": failures,
        "what_to_improve": to_improve,
        "output_preview": output_preview[:220],
        "strategy_score": meta_reasoning.get("strategy_score"),
        "recommended_shift": recommended_shift,
        "reflected_at": datetime.now(tz=UTC).isoformat(),
    }


def build_meta_reasoning_prompt_template(
    *,
    role: str,
    goal: str,
    retrieval_contract: str,
    retrieval_sections: list[str],
    selected_skills: list[str],
    prior_reflections: list[dict[str, Any]],
) -> str:
    """Create reusable meta-reasoning prompt block for supervisor/sub-agent cycles."""

    recent = prior_reflections[-3:]
    reflection_lines: list[str] = []
    for row in recent:
        shift = str(row.get("recommended_shift") or "maintain_strategy")
        score = row.get("strategy_score")
        reflection_lines.append(f"- shift={shift} score={score}")
    reflection_text = "\n".join(reflection_lines) if reflection_lines else "- no prior reflections yet"

    return (
        "## Meta-Reasoning Template\n"
        f"Role: {role}\n"
        f"Goal: {goal[:320]}\n"
        f"Retrieval contract: {retrieval_contract or 'none'}\n"
        f"Retrieval sections: {', '.join(retrieval_sections) if retrieval_sections else 'none'}\n"
        f"Skills in use: {', '.join(selected_skills) if selected_skills else 'none'}\n"
        "Reflection loop:\n"
        "1) What went well in this attempt?\n"
        "2) What failed or degraded quality?\n"
        "3) What should change in next strategy?\n"
        "Recent reflection memory:\n"
        f"{reflection_text}\n"
    ).strip()


def append_reflection_journal(
    *,
    context_summary: dict[str, Any],
    reflection: dict[str, Any] | None,
    meta_reasoning: dict[str, Any] | None,
    max_entries: int = 24,
) -> dict[str, Any]:
    """Persist compact reflection trail in session context for future decisions."""

    updated = dict(context_summary or {})
    journal = [row for row in updated.get("meta_reflection_journal", []) if isinstance(row, dict)]
    if reflection is not None:
        journal.append(dict(reflection))
    if len(journal) > max_entries:
        journal = journal[-max_entries:]
    updated["meta_reflection_journal"] = journal
    if meta_reasoning is not None:
        updated["meta_last_reasoning"] = dict(meta_reasoning)
    updated["meta_reflection_updated_at"] = datetime.now(tz=UTC).isoformat()
    return updated


__all__ = [
    "append_reflection_journal",
    "build_meta_reasoning_prompt_template",
    "build_reflection_cycle",
    "evaluate_meta_reasoning",
]
