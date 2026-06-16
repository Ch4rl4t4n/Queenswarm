"""Track L DA4 — Business question wizard → Mission Kanban + analytics session."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_kanban import create_mission_triage_task
from app.application.services.supervisor.session_service import create_supervisor_session
from app.application.services.supervisor.shared_context import SharedContextService
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.engine import OutputEngine

_logger = get_logger(__name__)

AnalyticsSourceId = Literal["ga4", "google_sheets", "warehouse_mcp", "hivemind"]
DateRangePreset = Literal["last_7d", "last_30d", "last_90d", "mtd", "qtd", "custom"]

ANALYTICS_TEMPLATE_ID = "business-analytics-report"
ANALYTICS_SKILL_SLUGS = [
    "business-analytics-playbook",
    "ga4-analytics-playbook",
    "self-review-loop",
    "context",
]

SOURCE_OPTIONS: tuple[tuple[AnalyticsSourceId, str], ...] = (
    ("ga4", "GA4 Data API (read-only)"),
    ("google_sheets", "Google Sheets read"),
    ("warehouse_mcp", "Warehouse MCP slot"),
    ("hivemind", "HiveMind recall"),
)

DATE_RANGE_PRESETS: tuple[tuple[DateRangePreset, str], ...] = (
    ("last_7d", "Last 7 days"),
    ("last_30d", "Last 30 days"),
    ("last_90d", "Last 90 days"),
    ("mtd", "Month to date"),
    ("qtd", "Quarter to date"),
    ("custom", "Custom range"),
)


class AnalyticsSourceOptionOut(BaseModel):
    """Selectable data source for analytics report."""

    model_config = ConfigDict(extra="forbid")

    id: AnalyticsSourceId
    label: str


class AnalyticsDateRangePresetOut(BaseModel):
    """Date range preset row."""

    model_config = ConfigDict(extra="forbid")

    id: DateRangePreset
    label: str


class BusinessQuestionWizardOut(BaseModel):
    """Wizard snapshot for analytics workspace UI."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    generated_at: datetime
    min_question_chars: int = 12
    template_id: str = ANALYTICS_TEMPLATE_ID
    source_options: list[AnalyticsSourceOptionOut] = Field(default_factory=list)
    date_range_presets: list[AnalyticsDateRangePresetOut] = Field(default_factory=list)
    default_sources: list[AnalyticsSourceId] = Field(default_factory=lambda: ["ga4", "hivemind"])
    operator_hint: str = ""
    local_sovereign_active: bool = False
    local_model_slug: str | None = None
    inference_hint: str = ""


class BusinessQuestionPreviewIn(BaseModel):
    """Preview brief before dispatch."""

    model_config = ConfigDict(extra="forbid")

    business_question: str = Field(min_length=12, max_length=4000)
    date_range_preset: DateRangePreset = "last_30d"
    date_start: date | None = None
    date_end: date | None = None
    sources: list[AnalyticsSourceId] = Field(default_factory=lambda: ["ga4", "hivemind"])
    title: str | None = Field(default=None, min_length=3, max_length=500)

    @field_validator("sources")
    @classmethod
    def _sources_non_empty(cls, value: list[AnalyticsSourceId]) -> list[AnalyticsSourceId]:
        if not value:
            msg = "At least one data source is required."
            raise ValueError(msg)
        deduped = list(dict.fromkeys(value))
        return deduped[:8]


class BusinessQuestionPreviewOut(BaseModel):
    """Resolved range + brief preview."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    title: str
    date_range_label: str
    date_start: str
    date_end: str
    sources: list[AnalyticsSourceId]
    brief_markdown: str
    session_goal_preview: str


class BusinessQuestionSubmitIn(BusinessQuestionPreviewIn):
    """Submit question → kanban lineage + optional supervisor session."""

    model_config = ConfigDict(extra="forbid")

    dispatch_session: bool = True


class BusinessQuestionSubmitOut(BaseModel):
    """Mission Kanban task + workspace deliverable (+ optional session)."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    task_id: str
    deliverable_id: str
    title: str
    brief_markdown: str
    href: str
    supervisor_session_id: str | None = None
    session_href: str | None = None
    message: str = ""


def compose_business_question_wizard_snapshot(
    *,
    local_sovereign_active: bool = False,
    local_model_slug: str | None = None,
    inference_hint: str = "",
) -> BusinessQuestionWizardOut:
    """Static wizard capabilities for analytics workspace."""

    if not settings.analytics_question_wizard_enabled:
        return BusinessQuestionWizardOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            operator_hint="Business Question wizard disabled.",
        )
    hint = "Enter one business question, pick date range and sources, then dispatch analytics session."
    if local_sovereign_active and inference_hint:
        hint = f"{inference_hint} {hint}"
    return BusinessQuestionWizardOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        source_options=[AnalyticsSourceOptionOut(id=sid, label=label) for sid, label in SOURCE_OPTIONS],
        date_range_presets=[AnalyticsDateRangePresetOut(id=pid, label=label) for pid, label in DATE_RANGE_PRESETS],
        operator_hint=hint,
        local_sovereign_active=local_sovereign_active,
        local_model_slug=local_model_slug,
        inference_hint=inference_hint,
    )


async def compose_business_question_wizard_snapshot_for_tenant(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> BusinessQuestionWizardOut:
    """Wizard snapshot enriched with LOC13 local sovereign inference lane."""

    from app.application.services.analytics_local_inference_service import resolve_analytics_local_inference

    local = await resolve_analytics_local_inference(session, tenant_id=tenant_id)
    return compose_business_question_wizard_snapshot(
        local_sovereign_active=local.active,
        local_model_slug=local.local_model_slug,
        inference_hint=local.operator_hint,
    )


def _resolve_date_range(
    preset: DateRangePreset,
    *,
    date_start: date | None,
    date_end: date | None,
) -> tuple[date, date, str]:
    """Resolve preset or custom dates to inclusive range + label."""

    today = datetime.now(tz=UTC).date()
    if preset == "custom":
        if date_start is None or date_end is None:
            raise ValueError("Custom range requires date_start and date_end.")
        if date_end < date_start:
            raise ValueError("date_end must be on or after date_start.")
        label = f"{date_start.isoformat()} → {date_end.isoformat()}"
        return date_start, date_end, label

    if preset == "last_7d":
        start = today - timedelta(days=6)
        return start, today, "Last 7 days"
    if preset == "last_30d":
        start = today - timedelta(days=29)
        return start, today, "Last 30 days"
    if preset == "last_90d":
        start = today - timedelta(days=89)
        return start, today, "Last 90 days"
    if preset == "mtd":
        start = today.replace(day=1)
        return start, today, "Month to date"
    if preset == "qtd":
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, quarter_month, 1)
        return start, today, "Quarter to date"
    raise ValueError(f"Unknown date_range_preset:{preset}")


def _source_labels(sources: list[AnalyticsSourceId]) -> list[str]:
    label_map = dict(SOURCE_OPTIONS)
    return [label_map.get(sid, sid) for sid in sources]


def compose_business_question_brief_markdown(
    *,
    business_question: str,
    date_range_label: str,
    date_start: date,
    date_end: date,
    sources: list[AnalyticsSourceId],
    title: str | None = None,
) -> tuple[str, str]:
    """Build analytics brief markdown and resolved title."""

    resolved_title = (title or "").strip() or business_question.strip()[:120]
    if len(resolved_title) < 3:
        resolved_title = "Business analytics report"
    source_lines = "\n".join(f"- {label}" for label in _source_labels(sources))
    lines = [
        f"# {resolved_title}",
        "",
        "_Generated by Business Question wizard — read-only fetch, critic ≥4/5 before export._",
        "",
        "## Business question",
        "",
        business_question.strip(),
        "",
        "## Date range",
        "",
        f"- **Label:** {date_range_label}",
        f"- **Start:** {date_start.isoformat()}",
        f"- **End:** {date_end.isoformat()}",
        "",
        "## Data sources (read-only)",
        "",
        source_lines,
        "",
        "## Guardrails",
        "",
        "- Follow `business-analytics-playbook` connector order.",
        "- Never mutate GA4 or warehouse configuration.",
        "- Export Notion/Slides simulate-first after critic rubric ≥4/5.",
        "- Tag every metric with connector · query · timestamp lineage.",
        "",
        "## Expected deliverables",
        "",
        "1. Fetch artifacts from selected sources.",
        "2. Analyst summary with cited deltas and anomalies.",
        "3. Executive narrative + chart specs in markdown.",
        "4. Critic score ≥4/5 before export staging.",
        "",
    ]
    return resolved_title, "\n".join(lines).strip() + "\n"


def _session_goal_from_brief(
    *,
    title: str,
    business_question: str,
    date_range_label: str,
    sources: list[AnalyticsSourceId],
    brief_markdown: str,
) -> str:
    """Supervisor goal for business-analytics-report session."""

    excerpt = brief_markdown[:2400]
    source_text = ", ".join(_source_labels(sources))
    return (
        f"Business analytics report using template `{ANALYTICS_TEMPLATE_ID}` (read-only, simulate-first).\n\n"
        f"Question: {business_question.strip()}\n"
        f"Date range: {date_range_label}\n"
        f"Sources: {source_text}\n\n"
        f"Workflow: fetch → analyze → narrative → critic rubric ≥4/5 → export simulate.\n"
        f"Skills: {', '.join(ANALYTICS_SKILL_SLUGS)}.\n\n"
        f"---\n{excerpt}\n---\n"
        f"Critic APPROVE before operator summary (≤400 words). No live export without approval."
    )


def preview_business_question_wizard(body: BusinessQuestionPreviewIn) -> BusinessQuestionPreviewOut:
    """Validate inputs and return brief + session goal preview."""

    if not settings.analytics_question_wizard_enabled:
        raise ValueError("analytics_question_wizard_disabled")

    start, end, range_label = _resolve_date_range(
        body.date_range_preset,
        date_start=body.date_start,
        date_end=body.date_end,
    )
    title, markdown = compose_business_question_brief_markdown(
        business_question=body.business_question,
        date_range_label=range_label,
        date_start=start,
        date_end=end,
        sources=body.sources,
        title=body.title,
    )
    goal = _session_goal_from_brief(
        title=title,
        business_question=body.business_question,
        date_range_label=range_label,
        sources=body.sources,
        brief_markdown=markdown,
    )
    return BusinessQuestionPreviewOut(
        ok=True,
        title=title,
        date_range_label=range_label,
        date_start=start.isoformat(),
        date_end=end.isoformat(),
        sources=body.sources,
        brief_markdown=markdown,
        session_goal_preview=goal[:1200],
    )


async def submit_business_question_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    created_by_subject: str,
    body: BusinessQuestionSubmitIn,
) -> BusinessQuestionSubmitOut:
    """Persist brief to Mission Kanban + workspace; optionally dispatch analytics session."""

    if not settings.analytics_question_wizard_enabled:
        raise ValueError("analytics_question_wizard_disabled")

    preview = preview_business_question_wizard(body)
    start = date.fromisoformat(preview.date_start)
    end = date.fromisoformat(preview.date_end)

    from app.application.services.analytics_local_inference_service import (
        append_local_inference_goal_note,
        build_analytics_session_local_context,
        resolve_analytics_local_inference,
    )

    local = await resolve_analytics_local_inference(session, tenant_id=tenant_id)

    triage = await create_mission_triage_task(
        session,
        task_text=preview.brief_markdown,
        title=preview.title,
        priority=6,
        swarm_id=None,
        skills=ANALYTICS_SKILL_SLUGS,
        extra_payload={
            "analytics_question_wizard": True,
            "wizard_template_id": ANALYTICS_TEMPLATE_ID,
            "business_question": body.business_question.strip(),
            "date_range_preset": body.date_range_preset,
            "date_start": preview.date_start,
            "date_end": preview.date_end,
            "sources": list(body.sources),
        },
    )
    task_id = triage.task.id
    lineage_id = uuid.uuid4()

    deliverable = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=lineage_id,
        markdown_body=preview.brief_markdown,
        structured={
            "format": "queenswarm.analytics_question.v1",
            "business_question": body.business_question.strip(),
            "date_range": {
                "preset": body.date_range_preset,
                "start": preview.date_start,
                "end": preview.date_end,
                "label": preview.date_range_label,
            },
            "sources": list(body.sources),
            "task_id": str(task_id),
            "template_id": ANALYTICS_TEMPLATE_ID,
        },
        title_hint=preview.title,
        slug_hint="analytics-question-brief",
        tags=["analytics", "business-question", "da4", "decision-report"],
        voice_script=None,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=None,
        mission_id=task_id,
        source_task_id=task_id,
    )

    supervisor_session_id: uuid.UUID | None = None
    session_href: str | None = None
    if body.dispatch_session:
        runtime_mode = "durable" if settings.supervisor_durable_mode_enabled else "inprocess"
        session_goal = append_local_inference_goal_note(
            goal=_session_goal_from_brief(
                title=preview.title,
                business_question=body.business_question,
                date_range_label=preview.date_range_label,
                sources=body.sources,
                brief_markdown=preview.brief_markdown,
            ),
            local=local,
        )
        sup = await create_supervisor_session(
            session,
            goal=session_goal,
            created_by_subject=created_by_subject,
            runtime_mode=runtime_mode,
            roles=["orchestrator", "researcher", "critic"],
            shared_context=SharedContextService(),
            retrieval_contract="customer_history+policy+last_3_tasks",
            skill_slugs=ANALYTICS_SKILL_SLUGS,
            tenant_id=tenant_id,
            context_seed={
                "analytics_question_wizard": True,
                "wizard_template_id": ANALYTICS_TEMPLATE_ID,
                "source_task_id": str(task_id),
                "deliverable_id": str(deliverable.id),
                "date_start": preview.date_start,
                "date_end": preview.date_end,
                "sources": list(body.sources),
                **build_analytics_session_local_context(local),
            },
        )
        supervisor_session_id = sup.id
        session_href = f"/agents#sessions?session={sup.id}"

    await session.flush()
    _ = start, end
    _logger.info(
        "analytics_question_wizard.submitted",
        agent_id="analytics_question_wizard",
        swarm_id=str(tenant_id),
        task_id=str(task_id),
        deliverable_id=str(deliverable.id),
        session_id=str(supervisor_session_id) if supervisor_session_id else None,
    )

    message = "Analytics brief saved to Mission Kanban and task workspace."
    if supervisor_session_id is not None:
        message = f"{message} Analytics session started."

    return BusinessQuestionSubmitOut(
        ok=True,
        task_id=str(task_id),
        deliverable_id=str(deliverable.id),
        title=preview.title,
        brief_markdown=preview.brief_markdown,
        href=f"/tasks?task={task_id}",
        supervisor_session_id=str(supervisor_session_id) if supervisor_session_id else None,
        session_href=session_href,
        message=message,
    )


__all__ = [
    "BusinessQuestionPreviewIn",
    "BusinessQuestionPreviewOut",
    "BusinessQuestionSubmitIn",
    "BusinessQuestionSubmitOut",
    "BusinessQuestionWizardOut",
    "compose_business_question_wizard_snapshot",
    "compose_business_question_wizard_snapshot_for_tenant",
    "preview_business_question_wizard",
    "submit_business_question_wizard",
]
