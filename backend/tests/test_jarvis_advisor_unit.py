"""Unit tests for POS-H Jarvis advisor + weak signal + agent quality."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.agent_quality_scorecard_service import compose_agent_quality_strip
from app.application.services.jarvis_advisor_service import (
    JarvisActionIn,
    JarvisApprovalIn,
    JarvisAutopilotIn,
    JarvisLifeOsIn,
    JarvisMemoryIn,
    JarvisMemoryLayerIn,
    JarvisSessionIn,
    _compose_jarvis_advisor_strip,
)
from app.application.services.weak_signal_bee_service import compose_weak_signal_preview


def test_jarvis_prioritizes_approvals_over_work() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.analytics_workspace_enabled = True
        mock_settings.research_bee_enabled = True
        mock_settings.closed_loop_presets_enabled = True

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[
                JarvisApprovalIn(
                    id="a1",
                    title="Publish post",
                    detail="Simulate passed — approve live.",
                    href="/cockpit#approvals",
                    kind="publish",
                ),
            ],
            active_sessions=[],
            next_actions=[
                JarvisActionIn(
                    id="d1",
                    title="Marketing draft",
                    detail="Write CZ post",
                    href="/apps-tools/marketing-team",
                    priority=2,
                ),
            ],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=True, routines_enabled=True),
            memory_strip=JarvisMemoryIn(usage_pct=80),
            weak_signal_hint=None,
        )

    assert strip.enabled is True
    assert len(strip.steps) == 3
    assert strip.steps[0].kind == "verify"
    assert "approval" in strip.steps[0].title.lower()


def test_jarvis_brain_pack_empty_when_usage_low() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.closed_loop_presets_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(
                usage_pct=5,
                layers=[
                    JarvisMemoryLayerIn(id="soul", label="SOUL", filled=False),
                ],
            ),
            weak_signal_hint=None,
        )

    titles = [step.title for step in strip.steps]
    assert any("Brain Pack" in title for title in titles)


def test_jarvis_suggests_cited_recall_when_brain_pack_ready() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.cited_recall_panel_enabled = True
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.closed_loop_presets_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(
                usage_pct=40,
                layers=[
                    JarvisMemoryLayerIn(id="soul", label="SOUL", filled=True),
                ],
            ),
            weak_signal_hint=None,
        )

    titles = [step.title for step in strip.steps]
    hrefs = [step.href for step in strip.steps]
    assert any("cited recall" in title.lower() for title in titles)
    assert "/knowledge?tab=memory#cited-recall" in hrefs


def test_jarvis_prioritizes_wiki_capture_approve() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.cited_recall_panel_enabled = False
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.closed_loop_presets_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(usage_pct=50),
            weak_signal_hint=None,
            pending_wiki_captures=2,
        )

    titles = [step.title.lower() for step in strip.steps]
    assert any("wiki capture" in title for title in titles)


def test_jarvis_suggests_agent_loop_for_running_session() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.closed_loop_presets_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[
                JarvisSessionIn(
                    session_id="sess-1",
                    goal="Refactor mission home",
                    status="running",
                    href="/agents?session=sess-1",
                ),
            ],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(usage_pct=50),
            weak_signal_hint=None,
        )

    titles = [step.title.lower() for step in strip.steps]
    hrefs = [step.href for step in strip.steps]
    assert any("watch agent loop" in title for title in titles)
    assert any(href.endswith("#agent-loop-timeline") for href in hrefs)


def test_jarvis_prioritizes_tool_outcomes_at_needs_input() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.closed_loop_presets_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[
                JarvisSessionIn(
                    session_id="sess-1",
                    goal="Publish draft",
                    status="needs_input",
                    href="/agents?session=sess-1",
                ),
            ],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(usage_pct=50),
            weak_signal_hint=None,
        )

    titles = [step.title.lower() for step in strip.steps]
    hrefs = [step.href for step in strip.steps]
    assert any("review tool outcomes" in title for title in titles)
    assert any(href.endswith("#tool-outcome-panel") for href in hrefs)


def test_jarvis_prioritizes_goldmine_deltas() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False
        mock_settings.closed_loop_presets_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(usage_pct=50),
            weak_signal_hint=None,
            goldmine_alert_count=2,
        )

    titles = [step.title.lower() for step in strip.steps]
    hrefs = [step.href for step in strip.steps]
    assert any("goldmine delta" in title for title in titles)
    assert any(href.endswith("#goldmine-alerts") for href in hrefs)


def test_jarvis_suggests_social_intel_score_to_task() -> None:
    with patch("app.application.services.jarvis_advisor_service.settings") as mock_settings:
        mock_settings.jarvis_advisor_mission_home_enabled = True
        mock_settings.closed_loop_presets_enabled = True
        mock_settings.analytics_workspace_enabled = False
        mock_settings.research_bee_enabled = False

        strip = _compose_jarvis_advisor_strip(
            first_run_complete=True,
            approvals=[],
            active_sessions=[],
            next_actions=[],
            life_os=JarvisLifeOsIn(enabled=False),
            autopilot=JarvisAutopilotIn(enabled=False),
            memory_strip=JarvisMemoryIn(usage_pct=50),
            weak_signal_hint=None,
            social_intel_signal_count=2,
        )

    titles = [step.title.lower() for step in strip.steps]
    hrefs = [step.href for step in strip.steps]
    assert any("score social intel" in title for title in titles)
    assert any(href.endswith("#research-bee") for href in hrefs)


@pytest.mark.asyncio
async def test_weak_signal_preview_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.weak_signal_bee_service.settings") as mock_settings:
        mock_settings.weak_signal_bee_enabled = False
        out = await compose_weak_signal_preview(session, tenant_id=uuid.uuid4())
    assert out.enabled is False


@pytest.mark.asyncio
async def test_agent_quality_strip_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.agent_quality_scorecard_service.settings") as mock_settings:
        mock_settings.agent_quality_scorecard_enabled = False
        out = await compose_agent_quality_strip(session, tenant_id=uuid.uuid4())
    assert out.enabled is False
