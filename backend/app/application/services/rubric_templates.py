"""Curated rubric templates for subjective output scoring (design, copy, UX)."""

from __future__ import annotations

from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)

RubricCategory = Literal["design", "copy", "product", "code", "accessibility"]


class RubricDimension(BaseModel):
    """One weighted subjective scoring dimension."""

    model_config = ConfigDict(extra="ignore")

    weight: float = Field(ge=0.0, le=1.0)
    prompt: str = Field(min_length=8, max_length=500)


class RubricTemplate(BaseModel):
    """Reusable evaluation rubric for workflow steps and harness scoring."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=8, max_length=500)
    category: RubricCategory
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    evaluation_criteria: dict[str, Any] = Field(default_factory=dict)


def _dim(weight: float, prompt: str) -> dict[str, Any]:
    return RubricDimension(weight=weight, prompt=prompt).model_dump()


RUBRIC_TEMPLATES: tuple[RubricTemplate, ...] = (
    RubricTemplate(
        id="design-ux",
        name="Design & UX",
        description="Score UI layouts, interaction flows, and visual hierarchy for clarity and consistency.",
        category="design",
        evaluation_criteria={
            "must_satisfy": [
                "Primary action is visually obvious within 3 seconds",
                "Information hierarchy supports scan-first reading",
                "States (loading, empty, error) are addressed or explicitly deferred",
            ],
            "measurable_signals": {
                "contrast_ratio": ">= 4.5:1 for body text (WCAG AA target)",
                "touch_targets": ">= 44px on mobile breakpoints",
            },
            "subjective_dimensions": {
                "visual_hierarchy": _dim(0.3, "Does layout guide the eye to the primary task?"),
                "consistency": _dim(0.25, "Do components match the design system tokens and patterns?"),
                "cognitive_load": _dim(0.25, "Is the screen free of unnecessary decisions and clutter?"),
                "delight": _dim(0.2, "Does micro-interaction feedback feel intentional without distraction?"),
            },
        },
    ),
    RubricTemplate(
        id="copy-marketing",
        name="Marketing Copy",
        description="Evaluate headlines, CTAs, and body copy for clarity, persuasion, and brand voice.",
        category="copy",
        evaluation_criteria={
            "must_satisfy": [
                "Single clear value proposition above the fold",
                "CTA verb is specific (not generic 'Submit' or 'Click here')",
                "Claims are verifiable or qualified — no fabricated stats",
            ],
            "measurable_signals": {
                "headline_words": "<= 12 words",
                "reading_grade": "<= 9th grade for broad audiences",
            },
            "subjective_dimensions": {
                "clarity": _dim(0.3, "Can a skimming reader grasp the offer in one pass?"),
                "persuasion": _dim(0.25, "Does copy motivate action without hype or pressure?"),
                "brand_voice": _dim(0.25, "Does tone match Queenswarm neon-dark / bee-hive voice?"),
                "specificity": _dim(0.2, "Are benefits concrete rather than abstract buzzwords?"),
            },
        },
    ),
    RubricTemplate(
        id="marketing-creative",
        name="Marketing Creative (Riverflow)",
        description="Score carousel, ad, and social creative copy for composition, accuracy, and CTA clarity.",
        category="copy",
        pass_threshold=0.75,
        evaluation_criteria={
            "must_satisfy": [
                "Primary message fits one screen / slide without scroll",
                "CTA is explicit and action-oriented",
                "No fabricated testimonials, stats, or guarantees",
            ],
            "measurable_signals": {
                "cta_words": "<= 5 words",
                "body_words_per_slide": "<= 40 words for carousel slides",
            },
            "subjective_dimensions": {
                "composition": _dim(0.3, "Is visual hierarchy implied in copy structure (headline → proof → CTA)?"),
                "accuracy": _dim(0.25, "Are claims qualified and free of overpromise?"),
                "cta_clarity": _dim(0.25, "Would a cold reader know exactly what happens on click?"),
                "brand_voice": _dim(0.2, "Does tone match curated brand pack voice bullets?"),
            },
        },
    ),
    RubricTemplate(
        id="brand-compliance",
        name="Brand Compliance",
        description="Check copy against forbidden claims, voice rules, and competitor tone boundaries.",
        category="copy",
        pass_threshold=0.8,
        evaluation_criteria={
            "must_satisfy": [
                "No forbidden claims from brand pack (guarantees, regulated promises)",
                "Voice matches approved tone (no off-brand slang or hype)",
                "Competitor names used only for factual comparison, not disparagement",
            ],
            "measurable_signals": {
                "forbidden_phrase_hits": "0 unqualified superlatives (best, guaranteed, risk-free)",
            },
            "subjective_dimensions": {
                "voice_match": _dim(0.35, "Does copy sound like example posts in brand pack?"),
                "claim_safety": _dim(0.35, "Are all claims defensible and properly qualified?"),
                "consistency": _dim(0.3, "Is terminology consistent with brand glossary?"),
            },
        },
    ),
    RubricTemplate(
        id="product-spec",
        name="Product Spec / PRD",
        description="Score PRDs and tracer-bullet specs for testability, scope control, and measurable outcomes.",
        category="product",
        evaluation_criteria={
            "must_satisfy": [
                "Problem statement names a specific user and pain",
                "Success criteria are measurable or falsifiable",
                "Non-goals explicitly bound scope",
                "Vertical slices are independently shippable",
            ],
            "measurable_signals": {
                "success_criteria_count": ">= 2 measurable criteria",
                "slice_count": "3-7 vertical slices",
            },
            "subjective_dimensions": {
                "testability": _dim(0.35, "Can each slice be verified via simulation or automated check?"),
                "scope_discipline": _dim(0.35, "Are non-goals strong enough to prevent scope creep?"),
                "operator_clarity": _dim(0.3, "Can an operator approve/reject without guessing intent?"),
            },
        },
    ),
    RubricTemplate(
        id="code-review",
        name="Code Review Quality",
        description="Subjective code review rubric for maintainability, safety, and hive conventions.",
        category="code",
        pass_threshold=0.75,
        evaluation_criteria={
            "must_satisfy": [
                "No hardcoded secrets or credentials",
                "Async I/O for network and database paths",
                "Type hints and explicit error types on public functions",
            ],
            "measurable_signals": {
                "test_coverage_delta": ">= 0 for changed backend modules",
                "diff_scope": "Focused diff — no unrelated refactors",
            },
            "subjective_dimensions": {
                "readability": _dim(0.3, "Would another bee engineer understand this in one read?"),
                "safety": _dim(0.35, "Are guardrails, validation, and sandbox boundaries respected?"),
                "hive_fit": _dim(0.35, "Does change match project conventions and bee-hive decomposition?"),
            },
        },
    ),
    RubricTemplate(
        id="accessibility",
        name="Accessibility (a11y)",
        description="Score UI and content for keyboard, screen-reader, and responsive accessibility.",
        category="accessibility",
        evaluation_criteria={
            "must_satisfy": [
                "Interactive controls are keyboard reachable with visible focus",
                "Images and icons have text alternatives or aria labels",
                "Form fields have associated labels or aria-labelledby",
            ],
            "measurable_signals": {
                "color_contrast": "WCAG AA for text and UI components",
                "motion": "Respects prefers-reduced-motion or documents exception",
            },
            "subjective_dimensions": {
                "keyboard_flow": _dim(0.35, "Can a keyboard-only user complete the primary flow?"),
                "screen_reader": _dim(0.35, "Are landmarks, headings, and live regions sensible?"),
                "responsive_a11y": _dim(0.3, "Do mobile/tablet layouts preserve accessibility affordances?"),
            },
        },
    ),
)

_TEMPLATE_BY_ID: dict[str, RubricTemplate] = {item.id: item for item in RUBRIC_TEMPLATES}


def list_rubric_templates() -> list[RubricTemplate]:
    """Return all curated rubric templates."""

    return list(RUBRIC_TEMPLATES)


def get_rubric_template(template_id: str) -> RubricTemplate | None:
    """Lookup one rubric template by id."""

    key = template_id.strip().lower()
    return _TEMPLATE_BY_ID.get(key)


def merge_rubric_into_criteria(
    base: dict[str, Any] | None,
    template_id: str,
) -> dict[str, Any]:
    """Merge a rubric template into existing workflow evaluation_criteria."""

    template = get_rubric_template(template_id)
    if template is None:
        msg = f"Unknown rubric template: {template_id}"
        raise ValueError(msg)

    merged: dict[str, Any] = dict(base or {})
    criteria = dict(template.evaluation_criteria)
    for key in ("must_satisfy", "measurable_signals", "subjective_dimensions"):
        if key not in criteria:
            continue
        existing = merged.get(key)
        if key == "must_satisfy" and isinstance(existing, list):
            merged[key] = list(dict.fromkeys([*existing, *criteria[key]]))
        elif key == "measurable_signals" and isinstance(existing, dict):
            merged[key] = {**existing, **criteria[key]}
        elif key == "subjective_dimensions" and isinstance(existing, dict):
            merged[key] = {**existing, **criteria[key]}
        else:
            merged[key] = criteria[key]

    merged["rubric_template_id"] = template.id
    merged["pass_threshold"] = template.pass_threshold
    return merged


async def evaluate_text_with_rubric(
    db: Any,
    *,
    text: str,
    template_id: str,
    swarm_id: str = "",
    workflow_id: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Score arbitrary text against a rubric template via the evaluator LLM."""

    from app.core.llm_router import LiteLLMRouter

    template = get_rubric_template(template_id)
    if template is None:
        msg = f"Unknown rubric template: {template_id}"
        raise ValueError(msg)

    trimmed = text.strip()
    if len(trimmed) < 8:
        msg = "Text to evaluate must be at least 8 characters."
        raise ValueError(msg)

    router = LiteLLMRouter()
    criteria = dict(template.evaluation_criteria)
    criteria["pass_threshold"] = template.pass_threshold
    criteria["rubric_template_id"] = template.id
    criteria["rubric_name"] = template.name

    scored = await router.evaluate(
        db,
        text=trimmed,
        criteria=criteria,
        swarm_id=swarm_id,
        workflow_id=workflow_id,
        task_id=task_id,
    )
    scored["rubric_template_id"] = template.id
    scored["rubric_name"] = template.name
    scored["pass_threshold"] = template.pass_threshold
    logger.info(
        "rubric_templates.evaluate",
        template_id=template.id,
        is_valid=scored.get("is_valid"),
        confidence=scored.get("confidence"),
    )
    return scored


__all__ = [
    "RubricTemplate",
    "evaluate_text_with_rubric",
    "get_rubric_template",
    "list_rubric_templates",
    "merge_rubric_into_criteria",
]
