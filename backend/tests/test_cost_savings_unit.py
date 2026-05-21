"""Unit tests for cost savings baseline heuristics."""

from __future__ import annotations

from app.application.services.cost_savings import quality_baseline_multiplier


def test_quality_baseline_multiplier_when_mini_model_then_high() -> None:
    assert quality_baseline_multiplier("openai/gpt-4o-mini") >= 5.0


def test_quality_baseline_multiplier_when_primary_grok_then_one() -> None:
    assert quality_baseline_multiplier("xai/grok-3") == 1.0
