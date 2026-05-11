"""Unit coverage for hive selection helpers and LangGraph compile smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.enums import AgentRole
from app.services.sub_swarm.graph import build_sub_swarm_workflow_graph
from app.services.sub_swarm.selection import pick_agent_for_step


def test_pick_agent_prefers_matching_role() -> None:
    """Role-aligned members should win the routing lottery."""

    scraper = MagicMock()
    scraper.role = AgentRole.SCRAPER
    learner = MagicMock()
    learner.role = AgentRole.LEARNER
    chosen = pick_agent_for_step(
        [learner, scraper],
        queen=None,
        preferred_role=AgentRole.SCRAPER,
    )
    assert chosen is scraper


def test_pick_agent_falls_back_to_queen() -> None:
    """When nobody matches the step role, the queen anchors fallback routing."""

    learner = MagicMock()
    learner.role = AgentRole.LEARNER
    queen = MagicMock()
    queen.role = AgentRole.BLOG_WRITER
    chosen = pick_agent_for_step(
        [learner],
        queen=queen,
        preferred_role=AgentRole.SCRAPER,
    )
    assert chosen is queen


def test_pick_agent_falls_back_to_any_member() -> None:
    """Colonies without a queen still route through the first worker."""

    learner = MagicMock()
    learner.role = AgentRole.LEARNER
    chosen = pick_agent_for_step(
        [learner],
        queen=None,
        preferred_role=AgentRole.SCRAPER,
    )
    assert chosen is learner


def test_pick_agent_raises_when_colony_empty() -> None:
    """Routing must fail fast if the sub-swarm lost every bee."""

    with pytest.raises(ValueError, match="no agents"):
        pick_agent_for_step([], queen=None, preferred_role=AgentRole.LEARNER)


def test_sub_swarm_workflow_graph_compiles() -> None:
    """LangGraph should accept the hive state schema without runtime wiring."""

    compiled = build_sub_swarm_workflow_graph().compile()
    assert compiled is not None
