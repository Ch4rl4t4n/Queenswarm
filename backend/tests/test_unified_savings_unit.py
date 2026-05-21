"""Unit coverage for unified savings aggregation."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services import unified_savings


@pytest.mark.asyncio
async def test_build_unified_savings_payload_merges_time_and_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Headline totals combine imputed time value and LLM savings."""

    async def _fake_time(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "hours_saved_total": 10.0,
            "hours_saved_projected_monthly": 12.0,
            "verified_task_count": 4,
            "breakdown": [],
            "disclaimer": "time",
        }

    async def _fake_llm(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "saved_usd": 3.5,
            "saved_pct": 70.0,
            "call_count": 20,
            "actual_usd": 1.5,
            "quality_baseline_usd": 5.0,
            "routing_mode": "free_first",
            "cost_guardian_enabled": True,
            "window_days": 30,
        }

    monkeypatch.setattr(unified_savings, "build_time_saved_payload", _fake_time)
    monkeypatch.setattr(unified_savings, "build_cost_savings_payload", _fake_llm)

    payload = await unified_savings.build_unified_savings_payload(
        session=SimpleNamespace(),
        tenant_id=uuid.uuid4(),
        window_days=30,
        hourly_rate_usd=50.0,
    )

    assert payload["headline"]["time_value_usd"] == 500.0
    assert payload["headline"]["llm_saved_usd"] == 3.5
    assert payload["headline"]["total_value_usd"] == 503.5
    assert payload["llm_savings_available"] is True


@pytest.mark.asyncio
async def test_build_unified_savings_payload_without_tenant_skips_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without tenant context only time ROI is included."""

    async def _fake_time(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "hours_saved_total": 2.0,
            "hours_saved_projected_monthly": 2.5,
            "verified_task_count": 1,
            "breakdown": [],
            "disclaimer": "time",
        }

    monkeypatch.setattr(unified_savings, "build_time_saved_payload", _fake_time)

    payload = await unified_savings.build_unified_savings_payload(
        session=SimpleNamespace(),
        tenant_id=None,
        window_days=14,
    )

    assert payload["headline"]["total_value_usd"] == 100.0
    assert payload["llm_savings"] is None
    assert payload["llm_savings_available"] is False
