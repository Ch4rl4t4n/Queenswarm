"""Unit coverage for skill export + HIVE.md generation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.services.hive_md_generator import generate_recipe_hive_md, generate_swarm_hive_md
from app.application.services.skill_export import build_export_bundle, build_skill_md, recipe_slug
from app.infrastructure.persistence.models.enums import SwarmPurpose
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.swarm import SubSwarm


def test_recipe_slug_when_special_chars_then_kebab_case() -> None:
    assert recipe_slug("Grill Me / Spec-Driven!!") == "grill-me-spec-driven"


def test_build_skill_md_when_verified_recipe_then_includes_front_matter() -> None:
    recipe = Recipe(
        id=uuid.uuid4(),
        name="Spec Driven Flow",
        description="Write specs before code.",
        topic_tags=["spec", "tdd"],
        workflow_template={
            "steps": [
                {
                    "description": "Draft spec",
                    "agent_role": "researcher",
                    "guardrails": {"no_code": "until spec approved"},
                },
                {"description": "Implement", "agent_role": "coder"},
            ],
        },
        success_count=8,
        fail_count=2,
        avg_pollen_earned=12.5,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime(2026, 5, 19, tzinfo=UTC),
        last_used_at=None,
        is_deprecated=False,
    )
    md = build_skill_md(recipe)
    assert md.startswith("---")
    assert "verified: true" in md
    assert "# Spec Driven Flow" in md
    assert "Draft spec" in md
    assert "no_code" in md


def test_build_export_bundle_when_recipe_then_six_files() -> None:
    recipe = Recipe(
        id=uuid.uuid4(),
        name="Export Test",
        description="d",
        topic_tags=["api"],
        workflow_template={"steps": [{"description": "step one"}]},
        success_count=1,
        fail_count=0,
        avg_pollen_earned=3.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=datetime.now(tz=UTC),
        last_used_at=None,
        is_deprecated=False,
    )
    bundle = build_export_bundle(recipe)
    assert bundle.meta.slug == "export-test"
    assert bundle.meta.verified is True
    paths = {f.path for f in bundle.files}
    assert f"{bundle.meta.slug}/SKILL.md" in paths
    assert f"{bundle.meta.slug}/HIVE.md" in paths
    assert f"{bundle.meta.slug}/tasks.prompt.md" in paths
    assert f"{bundle.meta.slug}/meta.json" in paths
    assert f"{bundle.meta.slug}/README.md" in paths
    assert f"{bundle.meta.slug}/LISTING.md" in paths
    assert bundle.publish is not None
    assert len(bundle.publish.channels) == 4
    assert "npx skills@latest add" in bundle.install_command


def test_generate_swarm_hive_md_when_local_memory_goals_then_renders() -> None:
    swarm = SubSwarm(
        id=uuid.uuid4(),
        name="Alpha Colony",
        purpose=SwarmPurpose.SCOUT,
        local_memory={
            "goals": ["Ship verified skills", "Keep pollen high"],
            "rules": ["Simulation before output"],
        },
        queen_agent_id=None,
        last_global_sync_at=None,
        total_pollen=42.0,
        member_count=5,
        is_active=True,
    )
    md = generate_swarm_hive_md(swarm)
    assert "# HIVE — Alpha Colony" in md
    assert "Ship verified skills" in md
    assert "Simulation before output" in md


def test_generate_recipe_hive_md_when_steps_present_then_lists_workflow() -> None:
    recipe = Recipe(
        id=uuid.uuid4(),
        name="Hive Recipe",
        description=None,
        topic_tags=[],
        workflow_template={"steps": [{"description": "analyze", "agent_role": "evaluator"}]},
        success_count=0,
        fail_count=0,
        avg_pollen_earned=0.0,
        embedding_id=None,
        created_by_agent_id=None,
        verified_at=None,
        last_used_at=None,
        is_deprecated=False,
    )
    md = generate_recipe_hive_md(recipe)
    assert "analyze" in md
    assert "evaluator" in md
