"""Unit tests for heuristic agentic pattern router."""

from __future__ import annotations

from app.application.services.supervisor.pattern_router import (
    PATTERN_PARALLELIZATION,
    PATTERN_PLANNING,
    PATTERN_REFLECTION,
    PATTERN_TOOL_USE,
    build_pattern_prompt_block,
    pattern_skill_slugs,
    select_patterns_for_task,
)


def test_select_patterns_when_parallel_goal_then_includes_parallelization() -> None:
    sel = select_patterns_for_task(
        goal="Run parallel batch analysis on all lead segments",
        roles=["researcher", "coder"],
    )
    assert PATTERN_PARALLELIZATION in sel.all_patterns()
    assert PATTERN_REFLECTION in sel.primary


def test_select_patterns_when_build_goal_then_includes_tool_use() -> None:
    sel = select_patterns_for_task(goal="Implement API integration and deploy", roles=["coder"])
    assert PATTERN_TOOL_USE in sel.all_patterns()


def test_select_patterns_when_planning_keywords_then_prompt_chaining() -> None:
    sel = select_patterns_for_task(goal="Create multi-step roadmap for Q3 launch", roles=["researcher"])
    patterns = sel.all_patterns()
    assert "prompt_chaining" in patterns
    assert PATTERN_PLANNING in patterns


def test_pattern_skill_slugs_when_reflection_selected_then_self_review() -> None:
    sel = select_patterns_for_task(goal="Verify report", roles=["critic"])
    slugs = pattern_skill_slugs(sel)
    assert "self-review-loop" in slugs


def test_build_pattern_prompt_block_includes_reflection_gate() -> None:
    sel = select_patterns_for_task(goal="test", roles=["coder"])
    block = build_pattern_prompt_block(sel)
    assert "Reflection gate" in block
    assert "Pattern Router" in block
