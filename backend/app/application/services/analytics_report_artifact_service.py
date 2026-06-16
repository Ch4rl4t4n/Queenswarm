"""Track L DA5 — Live analytics report artifact (session-bound, operator-editable)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.goal_progress_strip_service import compose_task_goal_progress
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.service import fetch_owned_deliverable, list_owned_deliverables, persist_final_deliverable
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_logger = get_logger(__name__)

ANALYTICS_REPORT_FORMAT = "queenswarm.analytics_report.v1"
ANALYTICS_ARTIFACT_TAGS = frozenset({"analytics", "decision-report", "business-question"})

ChartType = Literal["bar", "line", "kpi"]


class AnalyticsChartBlockOut(BaseModel):
    """One chart or KPI block bound to report artifact structured JSON."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    chart_type: ChartType
    title: str = Field(min_length=1, max_length=200)
    labels: list[str] = Field(default_factory=list, max_length=24)
    values: list[float] = Field(default_factory=list, max_length=24)
    unit: str = Field(default="", max_length=32)
    source_citation: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _validate_chart_shape(self) -> AnalyticsChartBlockOut:
        if self.chart_type == "kpi" and len(self.values) < 1:
            msg = "KPI chart blocks require at least one value."
            raise ValueError(msg)
        if self.chart_type in {"bar", "line"}:
            if len(self.values) < 1:
                msg = "Bar and line chart blocks require values."
                raise ValueError(msg)
            if self.labels and len(self.labels) != len(self.values):
                msg = "Labels and values length must match for bar/line charts."
                raise ValueError(msg)
        return self


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


def _is_analytics_deliverable(row: TaskFinalDeliverable) -> bool:
    tags = {str(t).strip().lower() for t in row.tags if isinstance(row.tags, list)}
    if tags & ANALYTICS_ARTIFACT_TAGS:
        return True
    structured = row.structured_json if isinstance(row.structured_json, dict) else {}
    fmt = str(structured.get("format") or "")
    return fmt.startswith("queenswarm.analytics")


def _parse_chart_blocks(structured: dict[str, Any]) -> list[AnalyticsChartBlockOut]:
    raw = structured.get("chart_blocks")
    if not isinstance(raw, list):
        return []
    blocks: list[AnalyticsChartBlockOut] = []
    for idx, item in enumerate(raw[:12]):
        if not isinstance(item, dict):
            continue
        try:
            blocks.append(
                AnalyticsChartBlockOut(
                    id=str(item.get("id") or f"chart-{idx + 1}"),
                    chart_type=item.get("chart_type") or item.get("type") or "kpi",
                    title=str(item.get("title") or "Metric"),
                    labels=[str(x) for x in item.get("labels", [])][:24],
                    values=[float(x) for x in item.get("values", [])][:24],
                    unit=str(item.get("unit") or ""),
                    source_citation=str(item.get("source_citation") or ""),
                ),
            )
        except (TypeError, ValueError):
            continue
    return blocks


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
        chart_blocks=_parse_chart_blocks(structured),
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
        if candidate is not None and _is_analytics_deliverable(candidate):
            row = candidate
    elif task_id is not None:
        rows = await list_owned_deliverables(
            session,
            dashboard_user_id=dashboard_user_id,
            limit=40,
            tag="analytics",
        )
        for candidate in rows:
            if candidate.source_task_id == task_id and _is_analytics_deliverable(candidate):
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
            if _is_analytics_deliverable(candidate):
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
    if row is None or not _is_analytics_deliverable(row):
        raise ValueError("analytics_artifact_not_found")

    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    structured["format"] = ANALYTICS_REPORT_FORMAT
    structured["chart_blocks"] = [block.model_dump() for block in body.chart_blocks]
    structured["operator_edited_at"] = datetime.now(tz=UTC).isoformat()
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
