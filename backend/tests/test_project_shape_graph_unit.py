"""Unit tests for project-shape graph labels and snapshot helpers."""

from __future__ import annotations

from app.domain.hive_mind.graph import _pick_label, _project_shape_peer_id


def test_pick_label_vault_document_uses_title() -> None:
    label = _pick_label("VaultDocument", {"title": "notes.md", "rel_path": "alpha/notes.md"})
    assert label == "notes.md"


def test_pick_label_vault_folder_uses_label() -> None:
    label = _pick_label("VaultFolder", {"label": "Research dump", "path": "graphify/t/batch"})
    assert label == "Research dump"


def test_pick_label_graphify_batch() -> None:
    label = _pick_label("GraphifyBatch", {"folder_label": "Q2 research", "batch_id": "abc"})
    assert "Q2 research" in label


def test_project_shape_peer_id_for_vault_folder() -> None:
    peer = _project_shape_peer_id(kind="VaultFolder", props={"path": "graphify/tenant/batch"})
    assert peer == "vf:graphify/tenant/batch"
