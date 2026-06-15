"""Unit tests for LOOP2 loop guardrails service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.loop_guardrails_service import (
    LoopGuardrailsPolicyOut,
    LoopGuardrailsPolicyPatchIn,
    _resolve_loop_status,
    build_loop_guardrails_context_seed,
    is_loop_guardrails_active,
    loop_max_turns_from_summary,
    min_score_to_five_scale,
    save_loop_guardrails_policy,
)


def test_build_loop_guardrails_context_seed_includes_caps() -> None:
    policy = LoopGuardrailsPolicyOut(enabled=True, max_turns=7, min_score=0.75, cost_cap_usd=1.25)
    seed = build_loop_guardrails_context_seed(policy)
    assert seed["loop_guardrails_enabled"] is True
    assert seed["loop_max_turns"] == 7
    assert seed["session_cost_cap_usd"] == 1.25


def test_is_loop_guardrails_active_false_for_maintainer() -> None:
    assert is_loop_guardrails_active({"queen_maintainer_lane": True, "loop_guardrails_enabled": True}) is False


def test_loop_max_turns_from_summary_reads_context() -> None:
    assert loop_max_turns_from_summary({"loop_max_turns": 9}) == 9


def test_min_score_to_five_scale() -> None:
    assert min_score_to_five_scale(0.8) == "4.0/5"


def test_resolve_loop_status_halt_on_turn_cap() -> None:
    status, alerts, action = _resolve_loop_status(
        turns_used=5,
        max_turns=5,
        cost_state="ok",
        min_score=0.8,
        last_score=None,
    )
    assert status == "halt"
    assert any("max turns" in row.lower() for row in alerts)
    assert "pause" in action.lower() or "approve" in action.lower()


@pytest.mark.asyncio
async def test_save_loop_guardrails_policy_persists_tenant_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    saved = await save_loop_guardrails_policy(
        session,
        tenant_id=tenant_id,
        patch=LoopGuardrailsPolicyPatchIn(max_turns=6, cost_cap_usd=0.75),
    )
    assert saved.max_turns == 6
    assert saved.cost_cap_usd == 0.75
    assert saved.source == "tenant"
    assert tenant.operator_settings["loop_guardrails"]["max_turns"] == 6
