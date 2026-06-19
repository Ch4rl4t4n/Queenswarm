"""Content Pack Factory API contract snapshot fields."""

from __future__ import annotations

from app.application.services.content_pack_factory_service import (
    ContentPackFactorySnapshotOut,
    ContentPackOpportunityOut,
    TenantContentPackOut,
)


def test_snapshot_out_schema_fields() -> None:
    fields = set(ContentPackFactorySnapshotOut.model_fields.keys())
    assert "policy" in fields
    assert "opportunities" in fields
    assert "library" in fields
    assert "queue_count" in fields
    assert "export_ready" in fields


def test_opportunity_out_includes_forge_suggestion_id() -> None:
    assert "forge_suggestion_id" in ContentPackOpportunityOut.model_fields


def test_library_out_includes_snippet_count() -> None:
    assert "snippet_count" in TenantContentPackOut.model_fields


def test_snapshot_includes_llm_readiness() -> None:
    fields = set(ContentPackFactorySnapshotOut.model_fields.keys())
    assert "llm" in fields
