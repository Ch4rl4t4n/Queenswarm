"""Unit tests for launch batch preparation service."""

from __future__ import annotations

from app.application.services.skill_factory_launch import LaunchPrepareOut


def test_launch_prepare_out_fields_for_fe() -> None:
    fields = set(LaunchPrepareOut.model_fields.keys())
    assert {
        "exported_count",
        "sellable_recommended",
        "tier_counts",
        "checklist_md",
        "exports",
        "message",
    } <= fields
