"""Sanity checks for task snapshot enrichments."""

from __future__ import annotations

import pytest

from app.services.task_presenter import (
    confidence_from_task_result,
    cost_usd_from_task_result,
)


def test_confidence_from_pct() -> None:
    """Confidence percent column should normalize to 0–1."""

    assert confidence_from_task_result({"confidence_pct": 91.0}) == pytest.approx(0.91)
    assert confidence_from_task_result(None) is None


def test_cost_from_result() -> None:
    """Optional spend metadata should parse as float."""

    assert cost_usd_from_task_result({"cost_usd": "0.02"}) == pytest.approx(0.02)
