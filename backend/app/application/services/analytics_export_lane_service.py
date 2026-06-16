"""Track L DA8 — Analytics export lane: Notion page + Google Slides (simulate-first)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_data_lineage_service import (
    _resolve_analytics_row,
    build_lineage_rows_from_deliverable,
)
from app.application.services.analytics_workspace_deliverable_utils import (
    parse_chart_blocks,
)
from app.application.services.goal_progress_strip_service import compose_task_goal_progress
from app.application.services.loop_guardrails_service import (
    last_rubric_score_from_summary,
    min_score_to_five_scale,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

_logger = get_logger(__name__)

AnalyticsExportDestination = Literal["notion", "slides"]
AnalyticsExportMode = Literal["simulate", "live"]

CRITIC_MIN_SCORE = 0.8  # 4.0/5 on five-point scale


class AnalyticsExportLaneSnapshotOut(BaseModel):
    """Operator snapshot for analytics export inbox."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    destinations: list[str]
    default_mode: AnalyticsExportMode
    notion_configured: bool
    slides_configured: bool
    critic_min_score_label: str
    operator_hint: str


class AnalyticsExportPreviewIn(BaseModel):
    """Preview export staging payload."""

    model_config = ConfigDict(extra="forbid")

    destination: AnalyticsExportDestination
    mode: AnalyticsExportMode = "simulate"
    deliverable_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    notion_parent_page_id: str | None = Field(default=None, max_length=64)
    slides_template_id: str | None = Field(default=None, max_length=128)


class AnalyticsExportPreviewOut(BaseModel):
    """Simulate-first preview before export submit."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    deliverable_id: str | None = None
    report_title: str | None = None
    destination: AnalyticsExportDestination
    mode: AnalyticsExportMode
    critic_score: float | None = None
    critic_score_label: str | None = None
    critic_passed: bool = False
    export_ready: bool = False
    notion_payload: dict[str, Any] | None = None
    slides_payload: dict[str, Any] | None = None
    lineage_count: int = 0
    chart_count: int = 0
    operator_hint: str = ""


class AnalyticsExportSubmitIn(BaseModel):
    """Submit export lane — simulate-first unless live + operator confirmed."""

    model_config = ConfigDict(extra="forbid")

    destination: AnalyticsExportDestination
    mode: AnalyticsExportMode = "simulate"
    deliverable_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None
    notion_parent_page_id: str | None = Field(default=None, max_length=64)
    slides_template_id: str | None = Field(default=None, max_length=128)
    operator_confirmed: bool = False


class AnalyticsExportSubmitOut(BaseModel):
    """Export lane execution result."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    deliverable_id: str | None = None
    destination: AnalyticsExportDestination
    mode: AnalyticsExportMode
    simulated: bool
    critic_passed: bool
    message: str
    notion_result: dict[str, Any] | None = None
    slides_result: dict[str, Any] | None = None


def _markdown_sections(markdown_body: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) sections."""

    sections: list[tuple[str, str]] = []
    current_title = "Executive summary"
    current_lines: list[str] = []
    for line in markdown_body.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = line.lstrip("#").strip() or "Section"
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines or not sections:
        sections.append((current_title, "\n".join(current_lines).strip()))
    return sections[:12]


def _notion_page_payload(
    *,
    parent_page_id: str | None,
    title: str,
    markdown_body: str,
    chart_blocks: list[dict[str, Any]],
    lineage_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build Notion create_page body (simulate-first)."""

    children: list[dict[str, Any]] = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": markdown_body[:1800]}}],
            },
        },
    ]
    for block in chart_blocks[:6]:
        label = str(block.get("title") or "Chart")
        values = block.get("values") or []
        val_text = ", ".join(str(v) for v in values[:6]) if values else "—"
        children.append(
            {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": f"{label}: {val_text} {block.get('unit') or ''}".strip()},
                        },
                    ],
                },
            },
        )
    if lineage_rows:
        children.append(
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "text": {"content": "Data lineage"}}]},
            },
        )
        for row in lineage_rows[:8]:
            detail = f"{row.get('connector_label')} · {row.get('query')} · {row.get('fetched_at')}"
            children.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": detail[:500]}}],
                    },
                },
            )

    parent: dict[str, Any]
    if parent_page_id:
        parent = {"page_id": parent_page_id}
    else:
        parent = {"type": "workspace", "workspace": True}

    return {
        "parent": parent,
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title[:2000]}}]},
        },
        "children": children[:50],
    }


def _slides_payload(
    *,
    template_id: str | None,
    title: str,
    markdown_body: str,
    chart_blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build Google Slides batchUpdate simulation payload."""

    slides: list[dict[str, Any]] = [
        {
            "layout": "TITLE",
            "title": title[:200],
            "subtitle": "Queenswarm analytics report — simulate-first export",
        },
    ]
    for heading, body in _markdown_sections(markdown_body):
        slides.append(
            {
                "layout": "TITLE_AND_BODY",
                "title": heading[:120],
                "body": body[:3000],
            },
        )
    for block in chart_blocks[:4]:
        values = block.get("values") or []
        val_text = values[0] if values else "—"
        slides.append(
            {
                "layout": "TITLE_AND_BODY",
                "title": str(block.get("title") or "KPI")[:120],
                "body": f"{val_text} {block.get('unit') or ''}\n{block.get('source_citation') or ''}".strip(),
            },
        )
    return {
        "presentation_title": title[:200],
        "template_id": template_id or "queenswarm-analytics-leadership",
        "slide_count": len(slides),
        "slides": slides,
        "requests_preview": [
            {"createSlide": {"slideLayoutReference": {"predefinedLayout": s["layout"]}}}
            for s in slides[:20]
        ],
    }


async def _resolve_critic_score(
    session: AsyncSession,
    *,
    structured: dict[str, Any],
    task_id: uuid.UUID | None,
) -> float | None:
    """Resolve critic rubric score (0–1) from deliverable or linked session."""

    for key in ("critic_rubric_score", "loop_last_rubric_score"):
        raw = structured.get(key)
        if isinstance(raw, (int, float)):
            val = float(raw)
            return val if val <= 1.0 else val / 5.0

    raw_five = structured.get("critic_score_5")
    if isinstance(raw_five, (int, float)):
        return max(0.0, min(float(raw_five) / 5.0, 1.0))

    if task_id is None:
        return None

    progress = await compose_task_goal_progress(session, task_id=task_id)
    if progress.session_id is None:
        return None

    sup = await session.scalar(
        select(SupervisorSession).where(SupervisorSession.id == progress.session_id),
    )
    if sup is None:
        return None
    summary = sup.context_summary if isinstance(sup.context_summary, dict) else {}
    return last_rubric_score_from_summary(summary)


async def compose_analytics_export_lane_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> AnalyticsExportLaneSnapshotOut:
    """Return export lane capabilities for analytics workspace."""

    if not settings.analytics_export_lane_enabled:
        return AnalyticsExportLaneSnapshotOut(
            enabled=False,
            destinations=[],
            default_mode="simulate",
            notion_configured=False,
            slides_configured=False,
            critic_min_score_label=min_score_to_five_scale(CRITIC_MIN_SCORE),
            operator_hint="Analytics export lane disabled.",
        )

    notion_ok = False
    slides_ok = False
    svc = DynamicConnectorService()
    notion_row = await svc.fetch_by_slug(session, slug="notion_workspace")
    if notion_row is not None and notion_row.is_active:
        notion_ok = True
    sheets_row = await svc.fetch_by_slug(session, slug="google_sheets")
    if sheets_row is not None and sheets_row.is_active:
        slides_ok = True

    _logger.info(
        "analytics_export_lane.snapshot",
        agent_id="analytics_export_lane",
        swarm_id=str(dashboard_user_id),
        notion_configured=notion_ok,
        slides_configured=slides_ok,
    )

    return AnalyticsExportLaneSnapshotOut(
        enabled=True,
        destinations=["notion", "slides"],
        default_mode="simulate",
        notion_configured=notion_ok,
        slides_configured=slides_ok,
        critic_min_score_label=min_score_to_five_scale(CRITIC_MIN_SCORE),
        operator_hint=(
            "Stage verified analytics report to Notion page or Google Slides leadership template — "
            "simulate-first until critic rubric ≥4/5 and operator approve."
        ),
    )


async def preview_analytics_export(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    body: AnalyticsExportPreviewIn,
) -> AnalyticsExportPreviewOut:
    """Build simulate-first export preview for active analytics artifact."""

    if not settings.analytics_export_lane_enabled:
        raise ValueError("analytics_export_lane_disabled")

    row = await _resolve_analytics_row(
        session,
        dashboard_user_id=dashboard_user_id,
        task_id=body.task_id,
        deliverable_id=body.deliverable_id,
    )
    if row is None:
        return AnalyticsExportPreviewOut(
            ok=False,
            destination=body.destination,
            mode=body.mode,
            operator_hint=(
                "No analytics report artifact — complete Question wizard dispatch and wait for narrative bee."
            ),
        )

    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    task_id = row.source_task_id
    critic_score = await _resolve_critic_score(session, structured=structured, task_id=task_id)
    critic_passed = critic_score is not None and critic_score >= CRITIC_MIN_SCORE
    chart_blocks = [block.model_dump() for block in parse_chart_blocks(structured)]
    lineage_rows = [
        {
            "section_label": item.section_label,
            "connector_label": item.connector_label,
            "query": item.query,
            "fetched_at": item.fetched_at,
        }
        for item in build_lineage_rows_from_deliverable(row)
    ]

    notion_payload: dict[str, Any] | None = None
    slides_payload: dict[str, Any] | None = None
    if body.destination == "notion":
        notion_payload = _notion_page_payload(
            parent_page_id=body.notion_parent_page_id,
            title=row.title,
            markdown_body=row.markdown_body,
            chart_blocks=chart_blocks,
            lineage_rows=lineage_rows,
        )
    else:
        slides_payload = _slides_payload(
            template_id=body.slides_template_id,
            title=row.title,
            markdown_body=row.markdown_body,
            chart_blocks=chart_blocks,
        )

    export_ready = critic_passed and len(row.markdown_body.strip()) >= 20
    hint_parts: list[str] = []
    if not critic_passed:
        score_label = min_score_to_five_scale(critic_score) if critic_score is not None else "missing"
        hint_parts.append(
            f"Critic rubric {score_label} — need ≥{min_score_to_five_scale(CRITIC_MIN_SCORE)} before live export.",
        )
    elif export_ready:
        hint_parts.append(f"Simulate-first — {len(chart_blocks)} chart(s), {len(lineage_rows)} lineage row(s) staged.")
    else:
        hint_parts.append("Report body too short — finish narrative before export.")

    return AnalyticsExportPreviewOut(
        ok=True,
        deliverable_id=str(row.id),
        report_title=row.title,
        destination=body.destination,
        mode=body.mode,
        critic_score=critic_score,
        critic_score_label=min_score_to_five_scale(critic_score) if critic_score is not None else None,
        critic_passed=critic_passed,
        export_ready=export_ready,
        notion_payload=notion_payload,
        slides_payload=slides_payload,
        lineage_count=len(lineage_rows),
        chart_count=len(chart_blocks),
        operator_hint=" ".join(hint_parts),
    )


async def submit_analytics_export(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: AnalyticsExportSubmitIn,
) -> AnalyticsExportSubmitOut:
    """Execute export lane — always simulate unless live + operator confirmed + critic passed."""

    preview = await preview_analytics_export(
        session,
        dashboard_user_id=dashboard_user_id,
        body=AnalyticsExportPreviewIn(
            destination=body.destination,
            mode=body.mode,
            deliverable_id=body.deliverable_id,
            task_id=body.task_id,
            notion_parent_page_id=body.notion_parent_page_id,
            slides_template_id=body.slides_template_id,
        ),
    )

    if not preview.ok or preview.deliverable_id is None:
        return AnalyticsExportSubmitOut(
            ok=False,
            destination=body.destination,
            mode=body.mode,
            simulated=True,
            critic_passed=False,
            message=preview.operator_hint,
        )

    if not preview.export_ready:
        return AnalyticsExportSubmitOut(
            ok=False,
            deliverable_id=preview.deliverable_id,
            destination=body.destination,
            mode=body.mode,
            simulated=True,
            critic_passed=preview.critic_passed,
            message=preview.operator_hint,
        )

    simulated = body.mode == "simulate" or not body.operator_confirmed
    notion_result: dict[str, Any] | None = None
    slides_result: dict[str, Any] | None = None

    if body.destination == "notion" and preview.notion_payload is not None:
        if not simulated:
            from app.application.services.execution_studio import execute_studio_tool
            from app.infrastructure.persistence.models.tenant import Tenant

            tenant = await session.get(Tenant, tenant_id)
            notion_result = await execute_studio_tool(
                session,
                dashboard_user_id=dashboard_user_id,
                tenant=tenant,
                connector_slug="notion_workspace",
                tool_name="create_page",
                arguments=preview.notion_payload,
                mode="live",
                manager_slug="content_creation",
                operator_confirmed=True,
            )
        else:
            notion_result = {
                "ok": True,
                "mode": "simulate",
                "executed": False,
                "preview": {
                    "connector_slug": "notion_workspace",
                    "tool_name": "create_page",
                    "arguments": preview.notion_payload,
                },
            }

    if body.destination == "slides" and preview.slides_payload is not None:
        slides_result = {
            "ok": True,
            "mode": "simulate" if simulated else "live",
            "executed": not simulated,
            "preview": preview.slides_payload,
            "detail": (
                "Google Slides batchUpdate staged — connect google_sheets OAuth for live deck creation."
                if simulated
                else "Live Slides export requires google_sheets connector — staged payload returned."
            ),
        }
        simulated = True  # Slides always simulate until dedicated connector ships

    dest_label = "Notion page" if body.destination == "notion" else "Google Slides deck"
    _logger.info(
        "analytics_export_lane.submit",
        agent_id="analytics_export_lane",
        swarm_id=str(tenant_id),
        deliverable_id=preview.deliverable_id,
        destination=body.destination,
        mode=body.mode,
        simulated=simulated,
        critic_passed=preview.critic_passed,
    )

    return AnalyticsExportSubmitOut(
        ok=True,
        deliverable_id=preview.deliverable_id,
        destination=body.destination,
        mode="simulate" if simulated else body.mode,
        simulated=simulated,
        critic_passed=preview.critic_passed,
        message=f"Staged {dest_label} for «{preview.report_title}» ({'simulate' if simulated else 'live'}).",
        notion_result=notion_result,
        slides_result=slides_result,
    )


__all__ = [
    "AnalyticsExportLaneSnapshotOut",
    "AnalyticsExportPreviewIn",
    "AnalyticsExportPreviewOut",
    "AnalyticsExportSubmitIn",
    "AnalyticsExportSubmitOut",
    "CRITIC_MIN_SCORE",
    "compose_analytics_export_lane_snapshot",
    "preview_analytics_export",
    "submit_analytics_export",
]
