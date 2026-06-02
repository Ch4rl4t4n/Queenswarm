"""Unit tests for Innovation Lab viability gate."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.innovation_viability_gate import assess_innovation_viability

_LONG_PLAN = "# Plan\n" + ("Implement safe feature with tests and docs. " * 4)


def _proposal(**overrides: object) -> MagicMock:
    row = MagicMock()
    row.id = uuid.uuid4()
    row.status = "approved"
    row.risk_level = "medium"
    row.title = "Innovation: test"
    row.description = "desc"
    row.implemented_at = None
    row.proposal_payload = {
        "source_prompt": "Add GA4 connector preset with simulate trust lane",
        "implementation_plan_md": _LONG_PLAN,
        "suggested_paths": ["backend/app/infrastructure/connectors/phase3/catalog.py"],
        "trust_lane": "simulate",
    }
    row.proposal_payload.update(overrides.get("proposal_payload") or {})  # type: ignore[arg-type]
    for key, value in overrides.items():
        if key != "proposal_payload":
            setattr(row, key, value)
    return row


@pytest.mark.asyncio
async def test_assess_innovation_viability_when_approved_then_passes() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    proposal = _proposal()

    with (
        patch("app.application.services.innovation_viability_gate.settings") as mock_settings,
        patch(
            "app.application.services.innovation_viability_gate.maintainer_run_precheck",
            new_callable=AsyncMock,
            return_value={"ok": True, "remaining_runs_today": "2/3"},
        ),
    ):
        mock_settings.hive_innovation_lab_enabled = True
        mock_settings.queen_maintainer_enabled = True
        out = await assess_innovation_viability(
            session,
            tenant_id=tenant_id,
            proposal=proposal,
        )

    assert out.ok is True
    assert out.status == "pass"
    assert not out.blocked_reasons


@pytest.mark.asyncio
async def test_assess_innovation_viability_when_plan_short_then_blocks() -> None:
    session = AsyncMock()
    proposal = _proposal(
        proposal_payload={
            "source_prompt": "Add GA4 connector preset with simulate trust lane",
            "implementation_plan_md": "# short",
            "trust_lane": "simulate",
        },
    )

    with (
        patch("app.application.services.innovation_viability_gate.settings") as mock_settings,
        patch(
            "app.application.services.innovation_viability_gate.maintainer_run_precheck",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ),
    ):
        mock_settings.hive_innovation_lab_enabled = True
        mock_settings.queen_maintainer_enabled = True
        out = await assess_innovation_viability(session, tenant_id=uuid.uuid4(), proposal=proposal)

    assert out.ok is False
    assert "plan_too_short" in out.blocked_reasons


@pytest.mark.asyncio
async def test_assess_innovation_viability_when_pre_tool_hit_then_blocks() -> None:
    session = AsyncMock()
    proposal = _proposal(
        proposal_payload={
            "source_prompt": "Add GA4 connector preset with simulate trust lane",
            "implementation_plan_md": _LONG_PLAN + "\nRun git push --force origin main",
            "trust_lane": "simulate",
        },
    )

    with (
        patch("app.application.services.innovation_viability_gate.settings") as mock_settings,
        patch(
            "app.application.services.innovation_viability_gate.maintainer_run_precheck",
            new_callable=AsyncMock,
            return_value={"ok": True},
        ),
    ):
        mock_settings.hive_innovation_lab_enabled = True
        mock_settings.queen_maintainer_enabled = True
        out = await assess_innovation_viability(session, tenant_id=uuid.uuid4(), proposal=proposal)

    assert out.ok is False
    assert "pre_tool_denylist" in out.blocked_reasons
