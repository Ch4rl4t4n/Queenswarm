"""Unit tests for recipe → supervisor routine conversion."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.application.services.supervisor.recipe_routine import (
    build_goal_template_from_recipe,
    infer_supervisor_roles_from_recipe,
    suggest_routine_name,
)


def _recipe(**overrides: object) -> SimpleNamespace:
    base = {
        "id": uuid.uuid4(),
        "name": "Verified — Lead Gen Lane",
        "description": "ICP to outreach drafts",
        "topic_tags": ["lead", "outreach"],
        "workflow_template": {
            "description": "Lead pipeline",
            "steps": [
                {"order": 1, "description": "Summarize ICP", "agent_role": "reporter"},
                {"order": 2, "description": "Scout leads", "agent_role": "scraper"},
                {"order": 3, "description": "Draft outreach", "agent_role": "evaluator"},
            ],
        },
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_infer_supervisor_roles_from_recipe_maps_agent_roles() -> None:
    roles = infer_supervisor_roles_from_recipe(_recipe())
    assert "researcher" in roles
    assert "critic" in roles


def test_build_goal_template_from_recipe_includes_steps() -> None:
    goal = build_goal_template_from_recipe(_recipe())
    assert "Lead Gen Lane" in goal
    assert "Step 1" in goal
    assert "simulate" in goal.lower()


def test_suggest_routine_name_slugifies() -> None:
    assert suggest_routine_name(_recipe()).startswith("recipe-")
