"""Track L DA5 — Live analytics report artifact (session-bound, operator-editable)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_data_lineage_service import (
    build_lineage_rows_from_payload,
    lineage_rows_to_structured,
)
from app.application.services.analytics_workspace_deliverable_utils import (
    ANALYTICS_REPORT_FORMAT,
    AnalyticsChartBlockOut,
    is_analytics_deliverable,
    parse_chart_blocks,
)
from app.application.services.goal_progress_strip_service import compose_task_goal_progress
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.service import fetch_owned_deliverable, list_owned_deliverables, persist_final_deliverable
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_logger = get_logger(__name__)


class AnalyticsReportArtifactOut(BaseModel):
    """Active analytics report artifact row for Apps & Tools panel."""

    model_config = ConfigDict(extra="forbid")

    deliverable_id: str
    lineage_id: str
    version: int
    title: str
    markdown_body: str
    chart_blocks: list[AnalyticsChartBlockOut] = Field(default_factory=list)
    task_id: str | None = None
    task_href: str | None = None
    session_id: str | None = None
    session_href: str | None = None
    session_status: str | None = None
    editable: bool = True
    updated_at: datetime
    format: str = ANALYTICS_REPORT_FORMAT


class AnalyticsReportArtifactSnapshotOut(BaseModel):
    """GET snapshot — active artifact or empty lane hint."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    has_artifact: bool
    artifact: AnalyticsReportArtifactOut | None = None
    empty_hint: str = ""


class AnalyticsReportArtifactPatchIn(BaseModel):
    """Operator save — markdown + optional chart blocks (version bump)."""

    model_config = ConfigDict(extra="forbid")

    markdown_body: str = Field(min_length=1, max_length=120_000)
    chart_blocks: list[AnalyticsChartBlockOut] = Field(default_factory=list, max_length=12)


def _merge_tags(existing: list[str]) -> list[str]:
    merged = list(dict.fromkeys([*existing, "analytics", "decision-report", "operator-edited"]))
    return merged[:32]


async def _session_context_for_task(
    session: AsyncSession,
    *,
    task_id: uuid.UUID,
) -> tuple[str | None, str | None, str | None]:
    progress = await compose_task_goal_progress(session, task_id=task_id)
    if not progress.visible or progress.session_id is None:
        return None, None, None
    return (
        str(progress.session_id),
        progress.session_href,
        progress.session_status,
    )


async def _artifact_from_row(
    session: AsyncSession,
    row: TaskFinalDeliverable,
) -> AnalyticsReportArtifactOut:
    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    task_id = row.source_task_id or _parse_uuid(structured.get("task_id"))
    session_id: str | None = None
    session_href: str | None = None
    session_status: str | None = None
    task_href = f"/tasks?task={task_id}" if task_id else None

    if task_id is not None:
        sid, href, status = await _session_context_for_task(session, task_id=task_id)
        session_id = sid
        session_href = href
        session_status = status

    return AnalyticsReportArtifactOut(
        deliverable_id=str(row.id),
        lineage_id=str(row.lineage_id),
        version=row.version,
        title=row.title,
        markdown_body=row.markdown_body,
        chart_blocks=parse_chart_blocks(structured),
        task_id=str(task_id) if task_id else None,
        task_href=task_href,
        session_id=session_id,
        session_href=session_href,
        session_status=session_status,
        editable=True,
        updated_at=row.created_at or datetime.now(tz=UTC),
        format=str(structured.get("format") or ANALYTICS_REPORT_FORMAT),
    )


def _parse_uuid(value: object) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


async def compose_analytics_report_artifact_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    task_id: uuid.UUID | None = None,
    deliverable_id: uuid.UUID | None = None,
) -> AnalyticsReportArtifactSnapshotOut:
    """Resolve active analytics report artifact for operator panel."""

    if not settings.analytics_report_artifact_enabled:
        return AnalyticsReportArtifactSnapshotOut(
            enabled=False,
            has_artifact=False,
            empty_hint="Report artifact panel disabled.",
        )

    row: TaskFinalDeliverable | None = None

    if deliverable_id is not None:
        candidate = await fetch_owned_deliverable(
            session,
            deliverable_id=deliverable_id,
            dashboard_user_id=dashboard_user_id,
        )
        if candidate is not None and is_analytics_deliverable(candidate):
            row = candidate
    elif task_id is not None:
        rows = await list_owned_deliverables(
            session,
            dashboard_user_id=dashboard_user_id,
            limit=40,
            tag="analytics",
        )
        for candidate in rows:
            if candidate.source_task_id == task_id and is_analytics_deliverable(candidate):
                row = candidate
                break
    else:
        rows = await list_owned_deliverables(
            session,
            dashboard_user_id=dashboard_user_id,
            limit=40,
            tag="analytics",
        )
        for candidate in rows:
            if is_analytics_deliverable(candidate):
                row = candidate
                break

    if row is None:
        return AnalyticsReportArtifactSnapshotOut(
            enabled=True,
            has_artifact=False,
            empty_hint=(
                "No analytics report yet — dispatch a business question from the Question tab "
                "or wait for the narrative bee to publish a deliverable."
            ),
        )

    artifact = await _artifact_from_row(session, row)
    return AnalyticsReportArtifactSnapshotOut(
        enabled=True,
        has_artifact=True,
        artifact=artifact,
    )


async def save_analytics_report_artifact(
    session: AsyncSession,
    *,
    deliverable_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    body: AnalyticsReportArtifactPatchIn,
) -> AnalyticsReportArtifactOut:
    """Persist operator edits as lineage version N+1."""

    if not settings.analytics_report_artifact_enabled:
        raise ValueError("analytics_report_artifact_disabled")

    row = await fetch_owned_deliverable(
        session,
        deliverable_id=deliverable_id,
        dashboard_user_id=dashboard_user_id,
    )
    if row is None or not is_analytics_deliverable(row):
        raise ValueError("analytics_artifact_not_found")

    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    structured["format"] = ANALYTICS_REPORT_FORMAT
    structured["chart_blocks"] = [block.model_dump() for block in body.chart_blocks]
    structured["operator_edited_at"] = datetime.now(tz=UTC).isoformat()
    lineage_rows = build_lineage_rows_from_payload(
        markdown_body=body.markdown_body.strip(),
        structured=structured,
    )
    structured["lineage_rows"] = lineage_rows_to_structured(lineage_rows)
    if row.source_task_id:
        structured["task_id"] = str(row.source_task_id)

    tags = row.tags if isinstance(row.tags, list) else []
    safe_tags = [str(t) for t in tags]

    saved = await persist_final_deliverable(
        session,
        lineage_id=row.lineage_id,
        dashboard_user_id=dashboard_user_id,
        ballroom_session_id=row.ballroom_session_id,
        mission_id=row.mission_id,
        source_task_id=row.source_task_id,
        slug_hint=row.slug,
        title_hint=row.title,
        markdown_body=body.markdown_body.strip(),
        structured=structured,
        tags=_merge_tags(safe_tags),
        voice_script=row.voice_script,
    )
    await session.flush()
    _logger.info(
        "analytics_report_artifact.saved",
        agent_id="analytics_report_artifact",
        swarm_id=str(dashboard_user_id),
        deliverable_id=str(saved.id),
        lineage_id=str(saved.lineage_id),
        version=saved.version,
    )
    return await _artifact_from_row(session, saved)


__all__ = [
    "AnalyticsChartBlockOut",
    "AnalyticsReportArtifactOut",
    "AnalyticsReportArtifactPatchIn",
    "AnalyticsReportArtifactSnapshotOut",
    "compose_analytics_report_artifact_snapshot",
    "save_analytics_report_artifact",
]
