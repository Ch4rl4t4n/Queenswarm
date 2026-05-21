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
    assert len(templates) >= 5


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
