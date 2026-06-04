"""BE/FE contract checks for Skill Factory API models."""

from __future__ import annotations

from app.application.services.skill_factory_service import SkillFactoryPolicyOut
from app.presentation.api.routers.skill_factory import SkillFactoryPolicyBody


def test_policy_body_matches_policy_out_fields() -> None:
    """Frontend PUT body fields must match backend policy out (prevents 422 on save)."""

    body_fields = set(SkillFactoryPolicyBody.model_fields.keys())
    out_fields = set(SkillFactoryPolicyOut.model_fields.keys())
    assert body_fields == out_fields, f"mismatch body-only={body_fields - out_fields} out-only={out_fields - body_fields}"


def test_snapshot_out_includes_connector_flags() -> None:
    """Dashboard snapshot exposes integration readiness flags for FE toggles."""

    from app.application.services.skill_factory_service import SkillFactorySnapshotOut

    fields = set(SkillFactorySnapshotOut.model_fields.keys())
    for required in (
        "research_keys_configured",
        "apify_connector_ready",
        "monid_connector_ready",
        "github_pr_export_ready",
        "gumroad_listing_ready",
        "gumroad_publish_ready",
        "launch_readiness",
        "launch_queue",
        "launch_near_miss",
        "llm",
    ):
        assert required in fields


def test_opportunity_out_includes_forge_quality_fields() -> None:
    from app.application.services.skill_factory_service import SkillOpportunityOut

    fields = set(SkillOpportunityOut.model_fields.keys())
    assert {"forge_quality_passed", "forge_critic_approved", "forge_issues"} <= fields


def test_launch_prepare_out_in_snapshot_contract_fields() -> None:
    """Launch prepare API uses LaunchPrepareOut — not embedded in snapshot."""

    from app.application.services.skill_factory_launch import LaunchPrepareOut

    assert "exports" in LaunchPrepareOut.model_fields
