"""Unit tests for NP6 Campaign launch wizard."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.campaign_launch_wizard_service import (
    CampaignLaunchDraftPatchIn,
    CampaignLaunchRubricRunIn,
    _brand_pack_step,
    _draft_copy_step,
    _progress_pct,
    _rubric_step,
    compose_campaign_launch_wizard_snapshot,
    patch_campaign_launch_wizard_draft,
    run_campaign_launch_rubric,
    submit_campaign_launch_wizard,
)
from app.application.services.campaign_launch_wizard_service import (
    CampaignBrandPackOut,
    CampaignLaunchDraftOut,
    CampaignLaunchRubricOut,
    CampaignLaunchStepOut,
)


def _ready_brand_packs() -> list[CampaignBrandPackOut]:
    return [
        CampaignBrandPackOut(
            id="queenswarm-default",
            label="Queenswarm default",
            source="builtin",
            detail="Default voice",
            ready=True,
        ),
    ]


def test_progress_pct_counts_done_steps() -> None:
    steps = [
        CampaignLaunchStepOut(id="brand_pack", label="A", status="done", detail=""),
        CampaignLaunchStepOut(id="draft_copy", label="B", status="pending", detail=""),
    ]
    assert _progress_pct(steps) == 50


def test_draft_copy_step_done_when_fields_valid() -> None:
    draft = CampaignLaunchDraftOut(
        title="Launch",
        body="A" * 25,
        cta="Try now",
        channel="instagram",
    )
    step = _draft_copy_step(draft=draft)
    assert step.status == "done"


def test_rubric_step_blocked_when_below_threshold() -> None:
    rubric = CampaignLaunchRubricOut(
        template_id="marketing-creative",
        template_name="Marketing Creative",
        score=0.6,
        pass_threshold=0.75,
        passed=False,
    )
    step = _rubric_step(rubric=rubric)
    assert step.status == "blocked"


def test_brand_pack_step_blocked_when_pack_not_ready() -> None:
    packs = [
        CampaignBrandPackOut(
            id="curated-brand",
            label="Brain Pack",
            source="tenant",
            detail="Fill Instructions",
            ready=False,
        ),
    ]
    draft = CampaignLaunchDraftOut(brand_pack_id="curated-brand")
    step = _brand_pack_step(draft=draft, brand_packs=packs)
    assert step.status == "blocked"


@pytest.mark.asyncio
async def test_compose_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "campaign_launch_wizard_enabled", False)
    snap = await compose_campaign_launch_wizard_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.enabled is False
    assert snap.steps == []


@pytest.mark.asyncio
async def test_patch_draft_resets_rubric(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "campaign_launch_wizard_enabled", True)
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "campaign_launch_wizard": {
                "body": "old body long enough here",
                "rubric_passed": True,
                "rubric_score": 0.9,
            },
        },
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.campaign_launch_wizard_service._compose_brand_packs",
        new=AsyncMock(return_value=_ready_brand_packs()),
    ):
        snapshot = await patch_campaign_launch_wizard_draft(
            db,
            tenant_id=tenant_id,
            patch=CampaignLaunchDraftPatchIn(body="Updated campaign body with enough chars."),
        )

    bucket = tenant.operator_settings["campaign_launch_wizard"]
    assert bucket["body"].startswith("Updated campaign")
    assert "rubric_passed" not in bucket
    assert snapshot.draft.body.startswith("Updated campaign")


@pytest.mark.asyncio
async def test_run_campaign_launch_rubric_persists_score(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "campaign_launch_wizard_enabled", True)
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=tenant_id,
        operator_settings={
            "campaign_launch_wizard": {
                "title": "Launch",
                "body": "Campaign body with enough characters for rubric scoring.",
                "cta": "Join",
            },
        },
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=tenant)

    with patch(
        "app.application.services.campaign_launch_wizard_service.evaluate_text_with_rubric",
        new=AsyncMock(
            return_value={
                "is_valid": True,
                "confidence": 0.82,
                "pass_threshold": 0.75,
                "feedback": "Strong CTA",
            },
        ),
    ):
        result = await run_campaign_launch_rubric(
            db,
            tenant_id=tenant_id,
            body=CampaignLaunchRubricRunIn(),
        )

    assert result.passed is True
    assert result.score == pytest.approx(0.82)
    bucket = tenant.operator_settings["campaign_launch_wizard"]
    assert bucket["rubric_passed"] is True


@pytest.mark.asyncio
async def test_submit_requires_rubric_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "campaign_launch_wizard_enabled", True)
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    with patch(
        "app.application.services.campaign_launch_wizard_service.compose_campaign_launch_wizard_snapshot",
        new=AsyncMock(
            return_value=SimpleNamespace(
                steps=[
                    SimpleNamespace(status="done", id="brand_pack", label="Brand"),
                    SimpleNamespace(status="done", id="draft_copy", label="Draft"),
                    SimpleNamespace(status="pending", id="rubric_score", label="Rubric"),
                ],
                rubric=SimpleNamespace(passed=False),
            ),
        ),
    ):
        with pytest.raises(ValueError, match="Complete wizard steps"):
            await submit_campaign_launch_wizard(
                AsyncMock(),
                tenant_id=tenant_id,
                dashboard_user_id=uuid.uuid4(),
                created_by_subject="operator@test",
            )
