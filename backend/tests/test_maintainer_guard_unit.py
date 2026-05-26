"""Unit tests for Queen Maintainer budget guard."""

from __future__ import annotations

from app.application.services.queen_maintainer.maintainer_guard import (
    MAINTAINER_LANE_KEY,
    append_maintainer_budget_goal_footer,
    build_maintainer_session_seed,
    is_maintainer_session,
    maintainer_approval_scan_text,
    maintainer_budget_snapshot,
    maintainer_session_cap_usd,
    maintainer_treats_context_satisfied,
)
from app.application.services.supervisor.runtime import detect_step_issues, is_approval_required


def test_build_maintainer_session_seed_includes_lane_and_cap() -> None:
    seed = build_maintainer_session_seed(trigger_source="execution_studio", pre_approved=True)
    assert seed["queen_maintainer_lane"] is True
    assert seed["session_cost_cap_usd"] == maintainer_session_cap_usd()
    assert seed["approval_state"] == "approve"
    assert seed["execution_studio_codebase_mode"] == "simulate"


def test_is_maintainer_session_when_flag_set() -> None:
    assert is_maintainer_session({"queen_maintainer_lane": True}) is True
    assert is_maintainer_session({}) is False


def test_append_maintainer_budget_goal_footer_mentions_cap() -> None:
    footer = append_maintainer_budget_goal_footer("Base goal")
    assert "Session LLM cap" in footer
    assert "simulate-first" in footer
    assert "grok-3-mini" in footer.lower() or "economy" in footer.lower()


def test_maintainer_budget_snapshot_remaining_runs() -> None:
    snap = maintainer_budget_snapshot(runs_today=1)
    assert snap["remaining_runs_today"] == 0
    assert snap["daily_run_limit"] >= 1


def test_maintainer_approval_scan_text_skips_curated_memory_drop_claim() -> None:
    goal = (
        "=== BEHAVIORAL INSTRUCTIONS ===\n"
        "DROP the claim when evidence is weak.\n"
        "=== END CONTEXT ===\n"
        "Queen Maintainer weekly run — PR-only codebase health review."
    )
    ctx = {MAINTAINER_LANE_KEY: True, "raw_goal": "Queen Maintainer weekly run"}
    assert "drop the claim" not in maintainer_approval_scan_text(goal=goal, context_summary=ctx).lower()
    required, reason = is_approval_required(goal=goal, toolset=[], context_summary=ctx)
    assert required is False, reason


def test_maintainer_approval_scan_text_respects_prior_approve() -> None:
    goal = "Queen Maintainer weekly run — drop table migration"
    ctx = {MAINTAINER_LANE_KEY: True, "approval_state": "approve"}
    required, _ = is_approval_required(goal=goal, toolset=[], context_summary=ctx)
    assert required is False


def test_maintainer_treats_context_satisfied_when_goal_embeds_tech_health() -> None:
    goal = append_maintainer_budget_goal_footer("Tech health score: 72 — review failing checks.")
    ctx = {MAINTAINER_LANE_KEY: True}
    assert maintainer_treats_context_satisfied(goal=goal, context_summary=ctx) is True
    issues = detect_step_issues(
        retrieval_contract="hive_mind:tech_health",
        retrieval_sections=[],
        selected_skills=["context"],
        output_text="Maintainer reviewed tech health and proposed PR-only fixes with enough detail.",
        goal=goal,
        context_summary=ctx,
    )
    assert "missing_context" not in issues
