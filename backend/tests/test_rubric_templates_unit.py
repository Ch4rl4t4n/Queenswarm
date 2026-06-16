"""Unit tests for rubric template catalog and merge helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.rubric_templates import (
    evaluate_text_with_rubric,
    get_rubric_template,
    list_rubric_templates,
    merge_rubric_into_criteria,
)


def test_list_rubric_templates_includes_design_and_copy() -> None:
    """Catalog should expose subjective scoring templates."""

    templates = list_rubric_templates()
    ids = {item.id for item in templates}
    assert "design-ux" in ids
    assert "copy-marketing" in ids
    assert "marketing-creative" in ids
    assert "brand-compliance" in ids
    assert "business-analytics-report" in ids
    assert len(templates) >= 8


def test_business_analytics_report_template_pass_threshold() -> None:
    """DA10 template should require ≥4/5 before export gate."""

    template = get_rubric_template("business-analytics-report")
    assert template is not None
    assert template.pass_threshold == 0.8
    assert template.category == "analytics"


def test_marketing_creative_template_has_riverflow_dimensions() -> None:
    """NP2 marketing-creative rubric exposes composition/accuracy/CTA/brand weights."""

    template = get_rubric_template("marketing-creative")
    assert template is not None
    assert template.pass_threshold == 0.75
    dims = template.evaluation_criteria.get("subjective_dimensions") or {}
    assert set(dims.keys()) == {"composition", "accuracy", "cta_clarity", "brand_voice"}


def test_brand_compliance_template_pass_threshold() -> None:
    """NP2 brand-compliance rubric should be stricter than marketing-creative."""

    template = get_rubric_template("brand-compliance")
    assert template is not None
    assert template.pass_threshold == 0.8


def test_merge_rubric_into_criteria_adds_template_metadata() -> None:
    """Merged criteria should include template id and pass threshold."""

    merged = merge_rubric_into_criteria({"must_satisfy": ["existing gate"]}, "product-spec")
    assert merged["rubric_template_id"] == "product-spec"
    assert merged["pass_threshold"] == 0.7
    assert "existing gate" in merged["must_satisfy"]
    assert "subjective_dimensions" in merged


def test_get_rubric_template_unknown_returns_none() -> None:
    """Unknown ids should not raise."""

    assert get_rubric_template("not-a-template") is None


@pytest.mark.asyncio
async def test_evaluate_text_with_rubric_delegates_to_llm_router() -> None:
    """Evaluate helper should call LiteLLMRouter.evaluate with template criteria."""

    db = AsyncMock()
    with patch("app.core.llm_router.LiteLLMRouter") as router_cls:
        router = router_cls.return_value
        router.evaluate = AsyncMock(
            return_value={"is_valid": True, "confidence": 0.82, "feedback": "Strong copy."},
        )
        result = await evaluate_text_with_rubric(
            db,
            text="Ship faster with verified agent swarms.",
            template_id="copy-marketing",
        )

    assert result["rubric_template_id"] == "copy-marketing"
    assert result["is_valid"] is True
    router.evaluate.assert_awaited_once()
