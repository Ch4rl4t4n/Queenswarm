"""Unit tests for OP2 four-lane Grok primary routing."""

from __future__ import annotations

from app.application.services.four_lane_llm_service import (
    build_four_lane_llm_context_seed,
    is_four_lane_session,
)


def test_is_four_lane_session_when_tagged() -> None:
    assert is_four_lane_session({"solo_operator_four_lane": True, "four_lane_id": "tech_scv"}) is True


def test_is_four_lane_session_when_lane_only() -> None:
    assert is_four_lane_session({"four_lane_id": "marketing_najman"}) is True


def test_build_four_lane_llm_context_seed_quality_mode() -> None:
    seed = build_four_lane_llm_context_seed()
    assert seed["four_lane_grok_primary"] is True
    assert seed["llm_routing_mode_override"] == "quality"
