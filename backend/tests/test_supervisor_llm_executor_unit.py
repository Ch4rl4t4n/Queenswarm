"""Unit tests for supervisor LLM executor + HiveMind insight ingest."""

from __future__ import annotations

from app.application.services.supervisor.hivemind_insight_ingest import extract_insight_markdown_blocks
from app.application.services.supervisor.llm_executor import resolve_system_prompt_for_role
from app.application.services.supervisor.runtime import is_approval_required


def test_extract_insight_markdown_blocks_when_hivemind_writeback_then_parsed() -> None:
    text = (
        "## Finding 1\n- claim: test\n\n"
        "## HiveMind write-back\n"
        "- title: [INSIGHT] Agent harness LLM wiring\n"
        "- body: #hivemind-candidate\n\nVerified wiring path.\n"
    )
    docs = extract_insight_markdown_blocks(text)
    assert docs
    assert "hivemind-candidate" in docs[0]["body"]


def test_resolve_system_prompt_for_role_researcher_has_hivemind_duty() -> None:
    prompt = resolve_system_prompt_for_role("researcher")
    assert "hivemind-candidate" in prompt.lower()
    assert "World Signals" in prompt


def test_is_approval_required_when_raw_goal_only_then_skips_curated_drop() -> None:
    goal = (
        "=== BEHAVIORAL INSTRUCTIONS ===\nDROP the claim when weak.\n=== END CONTEXT ===\n"
        "Sentinel HiveMind scan only."
    )
    required, reason = is_approval_required(
        goal=goal,
        toolset=[],
        context_summary={"raw_goal": "Sentinel HiveMind scan only."},
    )
    assert required is False, reason
