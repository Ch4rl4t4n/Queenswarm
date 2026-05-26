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
    assert len(snap.quick_automations) == 5
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
