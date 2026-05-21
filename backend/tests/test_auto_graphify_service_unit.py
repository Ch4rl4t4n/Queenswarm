"""Unit tests for Auto-Graphify folder ingest helpers."""

from __future__ import annotations

from app.application.services.auto_graphify_service import (
    AutoGraphifyService,
    _build_summary_md,
    _extract_tags,
)
from app.application.services.platform_features import resolve_platform_features


def test_extract_tags_from_path_and_hashtags() -> None:
    tags = _extract_tags(rel_path="projects/alpha/notes.md", text="See #Priority queue.")
    assert "projects" in tags
    assert "alpha" in tags
    assert "priority" in tags
    assert "auto_graphify" in tags


def test_build_summary_md_includes_graph_stats() -> None:
    md = _build_summary_md(
        folder_label="Research dump",
        file_count=4,
        items_ingested=3,
        graph_nodes_created=8,
        vectors_embedded=3,
        pollen_earned=4.5,
        vault_rel_path="graphify/tenant/batch",
    )
    assert "Auto-Graphify" in md
    assert "Graph nodes created" in md
    assert "4.5" in md
    assert "graphify/tenant/batch" in md


def test_commercial_pro_enables_auto_graphify_feature() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier="pro",
    )
    assert features["auto_graphify"] is True


def test_commercial_free_blocks_auto_graphify_feature() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier="free",
    )
    assert features["auto_graphify"] is False


def test_auto_graphify_service_repr() -> None:
    assert AutoGraphifyService.__name__ == "AutoGraphifyService"
