"""Track N NP2 — Creative rubric presets for publish simulate (Riverflow pattern)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.rubric_templates import (
    RubricTemplate,
    evaluate_text_with_rubric,
    get_rubric_template,
)
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

DEFAULT_PUBLISH_RUBRIC_TEMPLATE_ID = "marketing-creative"
BRAND_COMPLIANCE_TEMPLATE_ID = "brand-compliance"


class PublishCreativeRubricDimensionOut(BaseModel):
    """One weighted subjective dimension (composition, accuracy, …)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    weight: float
    score: float
    weighted_score: float


class PublishCreativeRubricOut(BaseModel):
    """NP2 weighted rubric snapshot attached to publish simulate."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    template_id: str
    template_name: str
    overall_score: float
    pass_threshold: float
    passed: bool
    dimensions: list[PublishCreativeRubricDimensionOut] = Field(default_factory=list)
    feedback: str = ""
    brand_compliance: dict[str, Any] | None = None
    operator_hint: str = ""


def compose_publish_pack_rubric_text(*, structured: dict[str, Any]) -> str:
    """Flatten publish pack fields into rubric-evaluable copy."""

    title = str(structured.get("title") or "").strip()
    body = str(structured.get("body") or "").strip()
    cta = str(structured.get("cta") or "").strip()
    tags = structured.get("hashtags") or []
    tag_line = " ".join(f"#{str(tag).lstrip('#')}" for tag in tags[:12])
    parts = [part for part in (title, body, f"CTA: {cta}" if cta else "", tag_line) if part]
    return "\n\n".join(parts)


def _parse_signal_score(raw: object, fallback: float) -> float:
    """Parse evaluator signal into 0..1 score."""

    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        value = float(raw)
        if value > 1.0:
            value = value / 100.0
        return max(0.0, min(value, 1.0))
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in {"pass", "ok", "yes", "true"}:
            return 1.0
        if lowered in {"fail", "no", "false"}:
            return 0.0
        pct = re.search(r"(\d+(?:\.\d+)?)\s*%", lowered)
        if pct:
            return max(0.0, min(float(pct.group(1)) / 100.0, 1.0))
        num = re.search(r"(\d+(?:\.\d+)?)", lowered)
        if num:
            value = float(num.group(1))
            if value > 1.0:
                value = value / 100.0
            return max(0.0, min(value, 1.0))
    return max(0.0, min(fallback, 1.0))


def build_weighted_dimension_breakdown(
    template: RubricTemplate,
    evaluation: dict[str, Any],
) -> tuple[list[PublishCreativeRubricDimensionOut], float]:
    """Map template subjective_dimensions + evaluator signals to weighted scores."""

    dims_cfg = dict(template.evaluation_criteria.get("subjective_dimensions") or {})
    signals = dict(evaluation.get("signals") or {})
    base_confidence = float(evaluation.get("confidence") or 0.0)
    dimensions: list[PublishCreativeRubricDimensionOut] = []
    weighted_sum = 0.0
    weight_sum = 0.0

    for dim_id, cfg in dims_cfg.items():
        if not isinstance(cfg, dict):
            continue
        weight = float(cfg.get("weight") or 0.0)
        label = str(dim_id).replace("_", " ").title()
        raw = signals.get(dim_id) or signals.get(label.lower()) or signals.get(str(dim_id).replace("_", " "))
        score = _parse_signal_score(raw, base_confidence)
        weighted = weight * score
        dimensions.append(
            PublishCreativeRubricDimensionOut(
                id=str(dim_id),
                label=label,
                weight=round(weight, 4),
                score=round(score, 4),
                weighted_score=round(weighted, 4),
            ),
        )
        weighted_sum += weighted
        weight_sum += weight

    overall = weighted_sum / weight_sum if weight_sum > 0 else base_confidence
    return dimensions, max(0.0, min(float(overall), 1.0))


def _evaluation_passed(*, evaluation: dict[str, Any], threshold: float, overall: float) -> bool:
    floor = max(threshold, float(evaluation.get("pass_threshold") or threshold))
    return bool(evaluation.get("is_valid")) and overall >= floor


def _rubric_from_evaluation(
    *,
    template: RubricTemplate,
    evaluation: dict[str, Any],
    include_brand: dict[str, Any] | None = None,
) -> PublishCreativeRubricOut:
    dimensions, overall = build_weighted_dimension_breakdown(template, evaluation)
    passed = _evaluation_passed(evaluation=evaluation, threshold=template.pass_threshold, overall=overall)
    feedback = str(evaluation.get("feedback") or evaluation.get("reasoning") or "").strip()
    hint = (
        f"Creative rubric pass ({overall:.0%} ≥ {template.pass_threshold:.0%}) — safe to queue simulate/live."
        if passed
        else f"Revise copy — weighted score {overall:.0%} below {template.pass_threshold:.0%} threshold."
    )
    return PublishCreativeRubricOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        template_id=template.id,
        template_name=template.name,
        overall_score=round(overall, 4),
        pass_threshold=template.pass_threshold,
        passed=passed,
        dimensions=dimensions,
        feedback=feedback[:2000],
        brand_compliance=include_brand,
        operator_hint=hint,
    )


async def evaluate_publish_pack_creative_rubric(
    session: AsyncSession,
    *,
    structured: dict[str, Any],
    template_id: str = DEFAULT_PUBLISH_RUBRIC_TEMPLATE_ID,
    deliverable_id: uuid.UUID | None = None,
    include_brand_compliance: bool = True,
) -> PublishCreativeRubricOut:
    """Score publish pack copy with NP2 marketing-creative (+ optional brand-compliance)."""

    now = datetime.now(tz=UTC)
    if not settings.rubric_templates_enabled or not settings.publish_creative_rubric_enabled:
        return PublishCreativeRubricOut(
            enabled=False,
            generated_at=now,
            template_id=template_id,
            template_name="",
            overall_score=0.0,
            pass_threshold=0.75,
            passed=False,
            operator_hint="Publish creative rubric disabled.",
        )

    template = get_rubric_template(template_id)
    if template is None:
        msg = f"Unknown rubric template: {template_id}"
        raise ValueError(msg)

    text = compose_publish_pack_rubric_text(structured=structured)
    if len(text.strip()) < 8:
        msg = "Publish pack copy too short for rubric evaluation."
        raise ValueError(msg)

    evaluation = await evaluate_text_with_rubric(
        session,
        text=text,
        template_id=template.id,
        swarm_id="publish_creative_rubric",
        task_id=str(deliverable_id or "publish_simulate"),
    )

    brand_payload: dict[str, Any] | None = None
    if include_brand_compliance and template_id == DEFAULT_PUBLISH_RUBRIC_TEMPLATE_ID:
        brand_template = get_rubric_template(BRAND_COMPLIANCE_TEMPLATE_ID)
        if brand_template is not None:
            brand_eval = await evaluate_text_with_rubric(
                session,
                text=text,
                template_id=brand_template.id,
                swarm_id="publish_creative_rubric",
                task_id=str(deliverable_id or "publish_simulate"),
            )
            brand_dims, brand_overall = build_weighted_dimension_breakdown(brand_template, brand_eval)
            brand_payload = {
                "template_id": brand_template.id,
                "overall_score": round(brand_overall, 4),
                "pass_threshold": brand_template.pass_threshold,
                "passed": _evaluation_passed(
                    evaluation=brand_eval,
                    threshold=brand_template.pass_threshold,
                    overall=brand_overall,
                ),
                "dimensions": [row.model_dump(mode="json") for row in brand_dims],
            }

    rubric = _rubric_from_evaluation(template=template, evaluation=evaluation, include_brand=brand_payload)
    _logger.info(
        "publish_creative_rubric.scored",
        agent_id="publish_creative_rubric",
        task_id=str(deliverable_id or ""),
        template_id=template.id,
        overall=rubric.overall_score,
        passed=rubric.passed,
    )
    return rubric


def creative_rubric_summary_from_structured(structured: dict[str, Any]) -> dict[str, Any] | None:
    """Load cached NP2 rubric blob from deliverable structured_json."""

    raw = structured.get("creative_rubric")
    if not isinstance(raw, dict):
        return None
    if not raw.get("enabled", True):
        return None
    return raw


__all__ = [
    "BRAND_COMPLIANCE_TEMPLATE_ID",
    "DEFAULT_PUBLISH_RUBRIC_TEMPLATE_ID",
    "PublishCreativeRubricDimensionOut",
    "PublishCreativeRubricOut",
    "build_weighted_dimension_breakdown",
    "compose_publish_pack_rubric_text",
    "creative_rubric_summary_from_structured",
    "evaluate_publish_pack_creative_rubric",
]
