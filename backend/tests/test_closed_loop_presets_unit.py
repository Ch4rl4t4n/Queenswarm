"""Unit tests for LOOP5 closed-loop presets."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.closed_loop_presets_service import (
    ClosedLoopPresetApplyIn,
    SocialIntelScoreIn,
    apply_closed_loop_preset,
    compose_closed_loop_presets_snapshot,
    get_closed_loop_preset,
    list_closed_loop_presets,
    run_social_intel_score_to_task,
)


def test_list_closed_loop_presets_has_factory_and_social() -> None:
    presets = list_closed_loop_presets()
    ids = {row.preset_id for row in presets}
    assert "factory_forge" in ids
    assert "social_intel" in ids
    assert "publish_bulk" in ids
    assert "analytics_report" in ids


def test_get_analytics_report_preset_metadata() -> None:
    preset = get_closed_loop_preset("analytics_report")
    assert preset is not None
    assert preset.rubric_template_id == "business-analytics-report"
    assert preset.min_score == 0.8
    assert preset.lane == "analytics"


def test_get_closed_loop_preset_returns_metadata() -> None:
    preset = get_closed_loop_preset("publish_bulk")
    assert preset is not None
    assert preset.simulate_only is True
    assert preset.rubric_template_id == "marketing-creative"


@pytest.mark.asyncio
async def test_compose_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "closed_loop_presets_enabled", False)
    snap = await compose_closed_loop_presets_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_apply_closed_loop_preset_persists_tenant_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "closed_loop_presets_enabled", True)
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})
    db = AsyncMock()
    db.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.closed_loop_presets_service.save_loop_guardrails_policy",
        new=AsyncMock(return_value=SimpleNamespace(source="tenant")),
    ):
        result = await apply_closed_loop_preset(
            db,
            tenant_id=tenant_id,
            body=ClosedLoopPresetApplyIn(preset_id="factory_forge"),
        )

    assert result.ok is True
    assert result.preset_id == "factory_forge"
    bucket = tenant.operator_settings["closed_loop_presets"]
    assert bucket["active_preset_id"] == "factory_forge"
    assert bucket["active_rubric_template_id"] == "code-review"


@pytest.mark.asyncio
async def test_run_social_intel_score_creates_task_on_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "closed_loop_presets_enabled", True)

    loop_result = SimpleNamespace(
        passed=True,
        message="Rubric pass on turn 1 (score 82%).",
        final_text="Verified intel summary for operator review.",
        iterations=[SimpleNamespace(score=0.82)],
    )

    with patch(
        "app.application.services.closed_loop_presets_service.run_closed_review_loop",
        new=AsyncMock(return_value=loop_result),
    ), patch(
        "app.application.services.closed_loop_presets_service.create_mission_triage_task",
        new=AsyncMock(return_value=SimpleNamespace(task=SimpleNamespace(id=uuid.uuid4()))),
    ), patch(
        "app.application.services.closed_loop_presets_service.OutputEngine.create_final_deliverable",
        new=AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
    ):
        result = await run_social_intel_score_to_task(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            body=SocialIntelScoreIn(
                text="Agent loop hype vs closed loops — operator must verify outcomes first.",
                create_task=True,
            ),
        )

    assert result.passed is True
    assert result.task_id is not None
