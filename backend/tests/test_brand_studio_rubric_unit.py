"""Unit tests for POS-I4 Brand studio rubric preview."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.brand_studio_rubric_service import (
    BrandStudioRubricPreviewIn,
    compose_brand_studio_snapshot,
    run_brand_studio_rubric_preview,
)
from app.application.services.brand_context_pack_service import BrandContextPackSnapshotOut
from app.application.services.publish_creative_rubric_service import PublishCreativeRubricOut


@pytest.mark.asyncio
async def test_brand_studio_snapshot_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.brand_studio_rubric_service.settings") as mock_settings:
        mock_settings.brand_studio_rubric_preview_enabled = False
        mock_settings.marketing_team_enabled = True
        snap = await compose_brand_studio_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is False


@pytest.mark.asyncio
async def test_brand_studio_snapshot_ready_brand() -> None:
    session = AsyncMock()
    brand = BrandContextPackSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        ready=True,
        char_count=420,
        usage_pct=12,
        sections=[],
    )
    with patch("app.application.services.brand_studio_rubric_service.settings") as mock_settings:
        mock_settings.brand_studio_rubric_preview_enabled = True
        mock_settings.marketing_team_enabled = True
        with patch(
            "app.application.services.brand_studio_rubric_service.compose_brand_context_pack_snapshot",
            AsyncMock(return_value=brand),
        ):
            snap = await compose_brand_studio_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.brand_ready is True
    assert snap.simulate_only is True
    assert "brand_pack" in snap.links


@pytest.mark.asyncio
async def test_brand_studio_rubric_preview_runs_creative_rubric() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    brand = BrandContextPackSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        ready=False,
        char_count=10,
    )
    rubric = PublishCreativeRubricOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        template_id="marketing-creative",
        template_name="Marketing Creative",
        overall_score=0.82,
        pass_threshold=0.75,
        passed=True,
        operator_hint="Strong CTA clarity.",
    )
    with patch("app.application.services.brand_studio_rubric_service.settings") as mock_settings:
        mock_settings.brand_studio_rubric_preview_enabled = True
        with patch(
            "app.application.services.brand_studio_rubric_service.compose_brand_context_pack_snapshot",
            AsyncMock(return_value=brand),
        ):
            with patch(
                "app.application.services.brand_studio_rubric_service.evaluate_publish_pack_creative_rubric",
                AsyncMock(return_value=rubric),
            ):
                result = await run_brand_studio_rubric_preview(
                    session,
                    tenant_id=tenant_id,
                    body=BrandStudioRubricPreviewIn(
                        title="Launch",
                        body="Verify-first outcomes beat hype every time for solo operators.",
                        cta="Start simulate-first",
                    ),
                )
    assert result.simulate_only is True
    assert result.rubric.passed is True
    assert "Brand pack incomplete" in result.operator_hint


@pytest.mark.asyncio
async def test_brand_studio_rubric_preview_rejects_short_body() -> None:
    with pytest.raises(Exception):
        BrandStudioRubricPreviewIn(body="too short")
