"""Unit tests for Phase 11.1 meta-reasoning helpers."""

from __future__ import annotations

from app.application.services.supervisor.meta_reasoning import (
    append_reflection_journal,
    build_meta_reasoning_prompt_template,
    build_reflection_cycle,
    evaluate_meta_reasoning,
)


def test_build_meta_reasoning_prompt_template_when_prior_reflections_then_includes_memory() -> None:
    prompt = build_meta_reasoning_prompt_template(
        role="critic",
        goal="Audit autonomy strategy",
        retrieval_contract="default_v2",
        retrieval_sections=["policy", "recent_events"],
        selected_skills=["meta-reasoning-reflection", "self-review-loop"],
        prior_reflections=[
            {"recommended_shift": "expand_retrieval_contract", "strategy_score": 0.66},
        ],
    )
    assert "Meta-Reasoning Template" in prompt
    assert "Recent reflection memory" in prompt
    assert "expand_retrieval_contract" in prompt


def test_build_reflection_cycle_when_unresolved_then_tracks_failures_and_improvements() -> None:
    meta = evaluate_meta_reasoning(
        role="researcher",
        goal="Collect constraints",
        retrieval_sections=[],
        selected_skills=[],
        issues=["missing_context", "bad_output"],
        alternatives=["Expand retrieval"],
        attempts=2,
        resolved=False,
    )
    reflection = build_reflection_cycle(
        role="researcher",
        goal="Collect constraints",
        attempt=2,
        issues=["missing_context", "bad_output"],
        resolved=False,
        output_preview="error output",
        meta_reasoning=meta,
    )
    assert reflection["what_failed"]
    assert reflection["what_to_improve"]
    assert reflection["recommended_shift"] == "expand_retrieval_contract"


def test_append_reflection_journal_when_overflow_then_keeps_recent_entries() -> None:
    summary: dict[str, object] = {}
    for idx in range(30):
        summary = append_reflection_journal(
            context_summary=summary,
            reflection={"attempt": idx, "recommended_shift": "maintain_strategy"},
            meta_reasoning={"strategy_score": 0.9},
            max_entries=10,
        )
    journal = summary["meta_reflection_journal"]
    assert isinstance(journal, list)
    assert len(journal) == 10
