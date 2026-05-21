"""Unit tests for orchestration recipe pattern tag resolution."""

from __future__ import annotations

from app.domain.recipes.orchestration_pattern_stacks import (
    enrich_workflow_template_patterns,
    infer_orchestration_template,
    list_orchestration_pattern_stacks,
    resolve_pattern_tags,
)


def test_resolve_pattern_tags_exec_assistant_by_name() -> None:
    meta = resolve_pattern_tags(
        name="Exec Assistant — Morning Brief",
        workflow_template={"kind": "ballroom_manager_lane"},
    )
    assert meta.orchestration_template == "exec_assistant"
    assert "planning" in meta.pattern_tags
    assert "reflection" in meta.pattern_tags


def test_resolve_pattern_tags_lead_waterfall_from_wizard_id() -> None:
    meta = resolve_pattern_tags(
        name="Custom sales flow",
        workflow_template={"swarm_wizard_id": "lead-waterfall", "steps": []},
    )
    assert meta.orchestration_template == "lead_waterfall"
    assert "parallelization" in meta.pattern_tags
    assert "human_in_the_loop" in meta.pattern_tags


def test_resolve_pattern_tags_uses_explicit_pattern_stack() -> None:
    meta = resolve_pattern_tags(
        name="Ad hoc",
        workflow_template={
            "orchestration_template": "research_swarm",
            "pattern_stack": ["rag", "exploration"],
        },
    )
    assert meta.pattern_tags == ["rag", "exploration"]


def test_enrich_workflow_template_injects_stack_for_life_os() -> None:
    enriched = enrich_workflow_template_patterns({"swarm_wizard_id": "life-os"})
    assert enriched["orchestration_template"] == "life_os"
    assert "memory_management" in enriched["pattern_stack"]
    assert "prioritization" in enriched["pattern_stack"]


def test_list_orchestration_pattern_stacks_includes_exec_and_life_os() -> None:
    stacks = list_orchestration_pattern_stacks()
    ids = {row["id"] for row in stacks}
    assert "exec_assistant" in ids
    assert "life_os" in ids


def test_infer_product_mission_from_seed_key() -> None:
    assert infer_orchestration_template(
        name="Product Mission — Revenue Swarm",
        workflow_template={"seed_key": "PRODUCT_MISSION"},
    ) == "product_mission"
