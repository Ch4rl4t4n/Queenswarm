"""Unit tests for Chief Business Operator snapshot (BA1)."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.business_operator import (
    BusinessCatalogSummaryOut,
    BusinessCatalogWaveSummaryOut,
    BusinessMissionSummaryOut,
    BusinessRevenueSummaryOut,
    _derive_top_actions,
    compose_business_operator_snapshot,
    compose_revenue_summary,
)


def test_compose_revenue_summary_parses_scorecard(tmp_path: Path) -> None:
    (tmp_path / "gumroad-ready").mkdir()
    (tmp_path / "business-simulations").mkdir(parents=True)
    (tmp_path / "guardrail-audits").mkdir(parents=True)
    (tmp_path / "model-evals").mkdir(parents=True)
    (tmp_path / "gumroad-ready" / "UPLOAD_QUEUE.md").write_text(
        "1. `hero-pack` (skill, score 100)\n",
        encoding="utf-8",
    )
    (tmp_path / "GUMROAD_SCORECARD.md").write_text("Ready: **14/16**\n", encoding="utf-8")
    (tmp_path / "business-simulations" / "GUMROAD_LAUNCH_STRATEGY.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "guardrail-audits" / "GUMROAD_OBJECTIVE_AUDIT.md").write_text("- v\n", encoding="utf-8")
    (tmp_path / "model-evals" / "MODEL_EVAL_REPORT.md").write_text("e\n", encoding="utf-8")
    (tmp_path / "OPERATOR_TOKEN_READINESS.md").write_text("t\n", encoding="utf-8")

    summary = compose_revenue_summary(tmp_path)
    assert summary.scorecard_ready_count == 14
    assert summary.first_upload_candidate is not None


def test_derive_top_actions_prioritizes_gumroad() -> None:
    actions = _derive_top_actions(
        revenue=BusinessRevenueSummaryOut(
            first_upload_candidate="`a`",
            next_operator_action="Upload",
        ),
        catalog=BusinessCatalogSummaryOut(product_count=10, gumroad_linked_count=0),
        catalog_wave=BusinessCatalogWaveSummaryOut(gap_to_mk6=0, current_wave="complete"),
        missions=BusinessMissionSummaryOut(),
        daily_items=[],
    )
    assert actions[0].id == "gumroad_first_upload"
    assert len(actions) <= 3


def test_derive_top_actions_prioritizes_mk6_wave() -> None:
    actions = _derive_top_actions(
        revenue=BusinessRevenueSummaryOut(missing_reports=[]),
        catalog=BusinessCatalogSummaryOut(product_count=14, gumroad_linked_count=5),
        catalog_wave=BusinessCatalogWaveSummaryOut(
            current_wave="wave_1",
            gap_to_mk6=36,
            scorecard_clean_count=14,
            mk6_target=50,
            next_operator_action="Run factory batches",
        ),
        missions=BusinessMissionSummaryOut(),
        daily_items=[],
    )
    assert actions[0].id == "factory_wave_mk6"


@pytest.mark.asyncio
async def test_compose_snapshot_disabled_when_control_plane_off() -> None:
    session = AsyncMock()
    with patch("app.application.services.business_operator.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        snapshot = await compose_business_operator_snapshot(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=MagicMock(),
        )
    assert snapshot.enabled is False
