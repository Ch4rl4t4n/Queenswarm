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
    ):
        assert required in fields
