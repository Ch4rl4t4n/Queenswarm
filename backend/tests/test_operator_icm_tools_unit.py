"""Unit tests for ICM operator tools (Link Drop, Dialogue Extract, keyword scan)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.operator_icm_tools import (
    compose_icm_tools_snapshot,
    extract_dialogue_structure,
    scan_transcript_keywords,
)


def test_compose_icm_tools_snapshot_when_enabled() -> None:
    with patch("app.application.services.operator_icm_tools.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.operator_icm_tools_enabled = True
        mock_settings.research_bee_enabled = True
        snap = compose_icm_tools_snapshot()
    assert snap.enabled is True
    assert len(snap.quick_automations) == 6
    assert any(p.id == "lead_gen_lane" for p in snap.quick_automations)
    assert any(p.id == "save_session_template" for p in snap.quick_automations)
    assert snap.link_drop_enabled is True


def test_compose_icm_tools_snapshot_when_disabled() -> None:
    with patch("app.application.services.operator_icm_tools.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.operator_icm_tools_enabled = False
        snap = compose_icm_tools_snapshot()
    assert snap.enabled is False
    assert snap.quick_automations == []


def test_extract_dialogue_structure_finds_goals_and_constraints() -> None:
    with patch("app.application.services.operator_icm_tools.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.operator_icm_tools_enabled = True
        text = (
            "User: Can you tighten this paragraph about climate change?\n"
            "Assistant: Here is a shorter version.\n"
            "User: Must keep the conversational rhythm and avoid jargon.\n"
            "User: Let's use the second draft. Next step: publish to blog.\n"
        )
        out = extract_dialogue_structure(text)
    assert out.enabled is True
    assert len(out.goals) >= 1
    assert any("rhythm" in c.lower() or "jargon" in c.lower() for c in out.constraints)
    assert out.task_prefill


def test_scan_transcript_keywords_incident() -> None:
    with patch("app.application.services.operator_icm_tools.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = True
        mock_settings.operator_icm_tools_enabled = True
        scan = scan_transcript_keywords("Production bug — API returns 500 on login.")
    assert scan.enabled is True
    assert any(m.id == "incident" for m in scan.matches)


def test_format_ballroom_transcript_text() -> None:
    from app.application.services.operator_icm_tools import format_ballroom_transcript_text

    text = format_ballroom_transcript_text(
        [
            {"agent": "You", "text": "Can you summarize our Q1 goals for the team?"},
            {"agent": "Orchestrator", "text": "Here is a concise summary of Q1 priorities."},
        ],
    )
    assert "User:" in text
    assert "Orchestrator:" in text
    assert len(text) >= 40


def test_build_dialogue_recipe_draft_min_steps() -> None:
    from app.application.services.operator_icm_tools import DialogueExtractOut, build_dialogue_recipe_draft

    extraction = DialogueExtractOut(
        enabled=True,
        generated_at=__import__("datetime").datetime.now(tz=__import__("datetime").UTC),
        goals=["Can you launch the new onboarding flow this week?"],
        next_steps=["Draft copy", "Run simulate-first review", "Publish after approval"],
        task_prefill="Launch onboarding flow this week with simulate-first guardrails.",
    )
    draft = build_dialogue_recipe_draft(extraction)
    assert len(draft["steps"]) >= 3
    assert draft["mark_verified"] is False
    assert "icm_tools" in draft["topic_tags"]


def test_format_dump_sleep_dialogue_text() -> None:
    from app.application.services.operator_icm_tools import format_dump_sleep_dialogue_text

    text = format_dump_sleep_dialogue_text(
        briefing_md="## Morning briefing\n\n- Must follow up on launch deadline by Friday.",
        voice_note_text="Remember to check the bug in checkout before standup.",
    )
    assert "User:" in text
    assert "Overnight briefing" in text
    assert len(text) >= 40


@pytest.mark.asyncio
async def test_build_session_recipe_draft_requires_completed() -> None:
    from app.application.services.operator_icm_tools import build_session_recipe_draft

    session = AsyncMock()
    row = MagicMock()
    row.tenant_id = uuid.uuid4()
    row.status = "running"
    row.goal = "Test goal for recipe draft with enough context."
    session.get = AsyncMock(return_value=row)

    with pytest.raises(ValueError, match="completed"):
        await build_session_recipe_draft(
            session,
            tenant_id=row.tenant_id,
            session_id=uuid.uuid4(),
        )
