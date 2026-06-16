"""Unit tests for NP2 publish creative rubric service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.publish_creative_rubric_service import (
    build_weighted_dimension_breakdown,
    compose_publish_pack_rubric_text,
    evaluate_publish_pack_creative_rubric,
)
from app.application.services.rubric_templates import get_rubric_template


def test_compose_publish_pack_rubric_text_includes_cta_and_tags() -> None:
    text = compose_publish_pack_rubric_text(
        structured={
            "title": "Launch day",
            "body": "Ship verified agent swarms.",
            "cta": "Start free",
            "hashtags": ["Queenswarm", "AI"],
        },
    )
    assert "Launch day" in text
    assert "Ship verified" in text
    assert "CTA: Start free" in text
    assert "#Queenswarm" in text


def test_build_weighted_dimension_breakdown_uses_signals() -> None:
    template = get_rubric_template("marketing-creative")
    assert template is not None
    dimensions, overall = build_weighted_dimension_breakdown(
        template,
        {
            "confidence": 0.7,
            "is_valid": True,
            "signals": {
                "composition": "0.9",
                "accuracy": "80%",
                "cta_clarity": "pass",
                "brand_voice": 0.65,
            },
        },
    )
    assert len(dimensions) == 4
    ids = {row.id for row in dimensions}
    assert ids == {"composition", "accuracy", "cta_clarity", "brand_voice"}
    assert overall > 0.7


@pytest.mark.asyncio
async def test_evaluate_publish_pack_creative_rubric_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_creative_rubric_service.settings",
        MagicMock(rubric_templates_enabled=False, publish_creative_rubric_enabled=False),
    )
    rubric = await evaluate_publish_pack_creative_rubric(
        AsyncMock(),
        structured={"body": "Enough copy for rubric scoring here."},
    )
    assert rubric.enabled is False


@pytest.mark.asyncio
async def test_evaluate_publish_pack_creative_rubric_returns_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.publish_creative_rubric_service.settings",
        MagicMock(rubric_templates_enabled=True, publish_creative_rubric_enabled=True),
    )
    with patch(
        "app.application.services.publish_creative_rubric_service.evaluate_text_with_rubric",
        AsyncMock(
            side_effect=[
                {
                    "is_valid": True,
                    "confidence": 0.82,
                    "feedback": "Strong CTA and clear hierarchy.",
                    "signals": {
                        "composition": 0.85,
                        "accuracy": 0.8,
                        "cta_clarity": 0.9,
                        "brand_voice": 0.75,
                    },
                },
                {
                    "is_valid": True,
                    "confidence": 0.88,
                    "signals": {"voice_match": 0.9, "claim_safety": 0.85, "consistency": 0.88},
                },
            ],
        ),
    ):
        rubric = await evaluate_publish_pack_creative_rubric(
            AsyncMock(),
            structured={
                "title": "Carousel slide 1",
                "body": "Verified workflows before you publish to social.",
                "cta": "Try Queenswarm",
            },
            deliverable_id=uuid.uuid4(),
        )

    assert rubric.enabled is True
    assert rubric.template_id == "marketing-creative"
    assert rubric.passed is True
    assert len(rubric.dimensions) == 4
    assert rubric.brand_compliance is not None
