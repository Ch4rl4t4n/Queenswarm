"""TR3 — Rubric score panel for session report pre-approve gate."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.loop_guardrails_service import (
    last_rubric_score_from_summary,
    loop_min_score_from_summary,
    min_score_to_five_scale,
)
from app.application.services.rubric_templates import get_rubric_template
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

RubricPreApproveStatus = Literal["ready", "below_floor", "pending", "unknown"]


class SessionReportRubricDimensionOut(BaseModel):
    """One weighted subjective dimension from the active rubric template."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    weight_pct: int = 0
    prompt: str = ""


class SessionReportRubricOut(BaseModel):
    """Operator-facing rubric block before approve in session report."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    visible: bool = False
    session_id: uuid.UUID
    session_status: str = ""
    pending_approval: bool = False
    template_id: str = ""
    template_name: str = ""
    template_category: str = ""
    pass_threshold_pct: float = 70.0
    score: float | None = None
    score_label: str | None = None
    min_score: float = 0.8
    min_score_label: str = "4.0/5"
    passed: bool | None = None
    pre_approve_status: RubricPreApproveStatus = "unknown"
    feedback: str | None = None
    deliverable_preview: str = ""
    dimensions: list[SessionReportRubricDimensionOut] = Field(default_factory=list)
    must_satisfy: list[str] = Field(default_factory=list)
    operator_hint: str = "Rubric score appears after closed-loop critic or harness evaluate."
    evaluate_href: str = "/settings#harness-loops-rubric"


def _clip(text: str, limit: int = 280) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 1]}…"


def _goal_blob(session) -> str:  # noqa: ANN001
    return str(getattr(session, "goal", "") or "").lower()


def _context_summary(session) -> dict[str, Any]:  # noqa: ANN001
    raw = getattr(session, "context_summary", None)
    return dict(raw) if isinstance(raw, dict) else {}


def infer_rubric_template_id(*, goal: str, context_summary: dict[str, Any]) -> str:
    """Pick the best rubric template for a session without LLM."""

    for key in ("loop_rubric_template_id", "active_rubric_template_id", "rubric_template_id"):
        candidate = str(context_summary.get(key) or "").strip().lower()
        if candidate and get_rubric_template(candidate) is not None:
            return candidate

    blob = goal.lower()
    if any(token in blob for token in ("design", " ui", "ux", "layout", "figma", "wireframe")):
        return "design-ux"
    if any(token in blob for token in ("code review", "refactor", "pull request", " pr ", "bugfix", "lint")):
        return "code-review"
    if any(token in blob for token in ("brand", "compliance", "voice pack", "forbidden claim")):
        return "brand-compliance"
    if any(token in blob for token in ("carousel", "creative", " ad ", "social post", "riverflow")):
        return "marketing-creative"
    if any(token in blob for token in ("copy", "landing", "headline", "cta", "marketing", "gumroad")):
        return "copy-marketing"
    if any(token in blob for token in ("accessibility", " a11y", "wcag", "screen reader")):
        return "accessibility"
    if any(token in blob for token in ("spec", "prd", "roadmap", "tracer")):
        return "product-spec"
    return "copy-marketing"


def _extract_deliverable_text(session) -> str:  # noqa: ANN001
    """Prefer reporter/critic outputs, then longest sub-agent output."""

    preferred_roles = ("reporter", "copywriter", "publisher", "critic", "reviewer", "writer")
    candidates: list[tuple[int, str]] = []
    for sub in getattr(session, "sub_agents", None) or []:
        role = str(getattr(sub, "role", "") or "").lower()
        output = str(getattr(sub, "last_output", None) or "").strip()
        if not output:
            memory = dict(getattr(sub, "short_memory", None) or {})
            output = str(memory.get("last_summary") or "").strip()
        if len(output) < 8:
            continue
        priority = preferred_roles.index(role) if role in preferred_roles else len(preferred_roles)
        candidates.append((priority, output))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: (item[0], -len(item[1])))
    return candidates[0][1]


def _template_dimensions(template_id: str) -> tuple[list[SessionReportRubricDimensionOut], list[str]]:
    template = get_rubric_template(template_id)
    if template is None:
        return [], []
    criteria = dict(template.evaluation_criteria or {})
    must_satisfy = [str(item).strip() for item in (criteria.get("must_satisfy") or []) if str(item).strip()]
    subjective = dict(criteria.get("subjective_dimensions") or {})
    dimensions: list[SessionReportRubricDimensionOut] = []
    for dim_id, row in subjective.items():
        if not isinstance(row, dict):
            continue
        weight = float(row.get("weight") or 0.0)
        dimensions.append(
            SessionReportRubricDimensionOut(
                id=str(dim_id),
                label=str(dim_id).replace("_", " ").title(),
                weight_pct=int(round(weight * 100)),
                prompt=str(row.get("prompt") or "").strip(),
            ),
        )
    return dimensions, must_satisfy


def _feedback_from_context(context_summary: dict[str, Any]) -> str | None:
    for key in ("loop_rubric_feedback", "loop_last_rubric_feedback", "rubric_feedback"):
        raw = str(context_summary.get(key) or "").strip()
        if raw:
            return _clip(raw, 320)
    return None


def _resolve_pre_approve_status(
    *,
    session_status: str,
    pending_approval: bool,
    passed: bool | None,
    score: float | None,
) -> RubricPreApproveStatus:
    normalized = session_status.strip().lower()
    if score is None:
        return "pending" if normalized == "needs_input" or pending_approval else "unknown"
    if passed is True:
        return "ready"
    if passed is False:
        return "below_floor"
    return "unknown"


def derive_session_report_rubric(
    *,
    session_id: uuid.UUID,
    session,  # noqa: ANN001
) -> SessionReportRubricOut:
    """Build TR3 rubric snapshot from session context (read-only, no LLM)."""

    summary = _context_summary(session)
    goal = str(getattr(session, "goal", "") or "")
    session_status = str(getattr(session, "status", "") or "")
    pending_approval = bool(summary.get("pending_operator_approval") or summary.get("approval_pending"))
    template_id = infer_rubric_template_id(goal=goal, context_summary=summary)
    template = get_rubric_template(template_id)
    dimensions, must_satisfy = _template_dimensions(template_id)
    deliverable = _extract_deliverable_text(session)
    score = last_rubric_score_from_summary(summary)
    min_score = loop_min_score_from_summary(summary)
    pass_threshold = float(template.pass_threshold if template is not None else settings.loop_guardrails_default_min_score)
    feedback = _feedback_from_context(summary)

    passed: bool | None = None
    if score is not None:
        floor = max(min_score, pass_threshold)
        passed = score >= floor

    pre_approve_status = _resolve_pre_approve_status(
        session_status=session_status,
        pending_approval=pending_approval,
        passed=passed,
        score=score,
    )

    normalized = session_status.strip().lower()
    visible = (
        normalized in {"needs_input", "completed", "failed"}
        or score is not None
        or len(deliverable) >= 8
        or pending_approval
    )

    if pre_approve_status == "ready" and normalized == "needs_input":
        hint = "Rubric meets verify floor — safe to approve live actions after tool outcome review."
    elif pre_approve_status == "below_floor":
        hint = (
            f"Score {min_score_to_five_scale(score or 0.0)} below floor "
            f"{min_score_to_five_scale(min_score)} — run Closed Review Loop or revise before approve."
        )
    elif pre_approve_status == "pending" and len(deliverable) >= 8:
        hint = (
            f"Deliverable ready — evaluate with rubric “{template.name if template else template_id}” "
            "in Harness → Loops before approving."
        )
    elif score is None:
        hint = "No rubric score stored yet — harness evaluate or closed review loop writes loop_last_rubric_score."
    else:
        hint = "Review subjective dimensions before exporting or approving live publish."

    return SessionReportRubricOut(
        enabled=True,
        visible=visible,
        session_id=session_id,
        session_status=session_status,
        pending_approval=pending_approval,
        template_id=template_id,
        template_name=template.name if template is not None else template_id.replace("-", " ").title(),
        template_category=str(template.category if template is not None else "copy"),
        pass_threshold_pct=round(pass_threshold * 100.0, 2),
        score=score,
        score_label=min_score_to_five_scale(score) if score is not None else None,
        min_score=min_score,
        min_score_label=min_score_to_five_scale(min_score),
        passed=passed,
        pre_approve_status=pre_approve_status,
        feedback=feedback,
        deliverable_preview=_clip(deliverable, 320),
        dimensions=dimensions,
        must_satisfy=must_satisfy[:5],
        operator_hint=hint,
    )


async def compose_session_report_rubric(
    session: AsyncSession,
    *,
    supervisor_session,  # noqa: ANN001
) -> SessionReportRubricOut:
    """Compose TR3 rubric panel for one supervisor session report."""

    if not settings.session_report_rubric_enabled:
        return SessionReportRubricOut(
            enabled=False,
            visible=False,
            session_id=supervisor_session.id,
        )

    if not settings.rubric_templates_enabled:
        return SessionReportRubricOut(
            enabled=False,
            visible=False,
            session_id=supervisor_session.id,
        )

    panel = derive_session_report_rubric(session_id=supervisor_session.id, session=supervisor_session)
    _logger.info(
        "session_report_rubric.composed",
        agent_id="session_report_rubric",
        swarm_id=str(getattr(supervisor_session, "tenant_id", "") or ""),
        task_id=str(supervisor_session.id),
        template_id=panel.template_id,
        pre_approve_status=panel.pre_approve_status,
        score=panel.score,
    )
    return panel


__all__ = [
    "SessionReportRubricDimensionOut",
    "SessionReportRubricOut",
    "compose_session_report_rubric",
    "derive_session_report_rubric",
    "infer_rubric_template_id",
]
