"""Unit tests for Verified Niche Harness export artifacts."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.skill_factory_export_harness import (
    build_eval_report_md,
    build_harness_md,
    build_tools_json,
)
from app.application.services.skill_export import build_export_bundle_from_tenant_skill


def _skill(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "id": "00000000-0000-0000-0000-000000000001",
        "slug": "seo-content-pipeline",
        "title": "SEO Content Pipeline",
        "description": "Simulate-first SEO workflow.",
        "markdown_body": (
            "---\nname: seo-pipeline\ndescription: SEO with guardrails\n---\n\n"
            "# SEO\n\nWhen to use: weekly content.\n\n1. Research\n2. Draft\n3. Simulate\n"
        ),
        "version": "1.0.0",
        "priority": 50,
        "roles": [],
        "keywords": ["seo", "content"],
        "source": "factory",
        "verified_at": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_tools_json_includes_mcp_schema() -> None:
    raw = build_tools_json(_skill())  # type: ignore[arg-type]
    assert "mcp_tools" in raw
    assert "verified_niche_harness" in raw


def test_build_export_bundle_from_tenant_skill_includes_harness_v2_files() -> None:
    bundle = build_export_bundle_from_tenant_skill(_skill())  # type: ignore[arg-type]
    paths = {f.path for f in bundle.files}
    assert "seo-content-pipeline/HARNESS.md" in paths
    assert "seo-content-pipeline/EVAL_REPORT.md" in paths
    assert "seo-content-pipeline/TOOLS.json" in paths
    assert "seo-content-pipeline/MCP_SETUP.md" in paths


def test_build_eval_report_md_lists_tier() -> None:
    md = build_eval_report_md(_skill(), forge_quality={"quality_gate_passed": True, "critic_approved": True})  # type: ignore[arg-type]
    assert "Tier:" in md
    assert "quality_gate_passed" in md


def test_build_harness_md_mentions_orchestrator() -> None:
    md = build_harness_md(_skill())  # type: ignore[arg-type]
    assert "Orchestrator" in md or "orchestrator" in md.lower()
