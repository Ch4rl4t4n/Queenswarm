"""Track L DA6 — Data lineage strip (connector · query · timestamp per section)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_workspace_deliverable_utils import (
    is_analytics_deliverable,
    parse_chart_blocks,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.service import fetch_owned_deliverable, list_owned_deliverables
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable

_logger = get_logger(__name__)

LineageBoundTo = Literal["chart", "markdown_section", "brief", "stored"]

CONNECTOR_LABELS: dict[str, str] = {
    "ga4": "GA4 Data API",
    "google_sheets": "Google Sheets read",
    "warehouse_mcp": "Warehouse MCP slot",
    "hivemind": "HiveMind recall",
    "notion_export": "Notion export staging",
}


class AnalyticsLineageRowOut(BaseModel):
    """One lineage row bound to a report section or chart block."""

    model_config = ConfigDict(extra="forbid")

    section_id: str
    section_label: str
    connector: str
    connector_label: str
    query: str
    fetched_at: str
    bound_to: LineageBoundTo = "chart"
    verified: bool = False
    detail: str = ""


class AnalyticsDataLineageSnapshotOut(BaseModel):
    """Lineage strip snapshot for analytics workspace."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    has_rows: bool
    deliverable_id: str | None = None
    deliverable_version: int | None = None
    report_title: str | None = None
    rows: list[AnalyticsLineageRowOut] = Field(default_factory=list)
    verified_count: int = 0
    gap_count: int = 0
    empty_hint: str = ""


def parse_source_citation(citation: str) -> tuple[str, str, str]:
    """Parse ``connector · query · timestamp`` citation string."""

    text = citation.strip()
    if not text:
        return "", "", ""
    parts = [part.strip() for part in text.split("·")]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return text, "", ""


def _connector_label(connector: str) -> str:
    key = connector.strip().lower().replace(" ", "_")
    if key in CONNECTOR_LABELS:
        return CONNECTOR_LABELS[key]
    lowered = connector.strip().lower()
    for slug, label in CONNECTOR_LABELS.items():
        if slug in lowered or label.lower() in lowered:
            return label
    return connector.strip() or "unknown"


def _lineage_row_from_parts(
    *,
    section_id: str,
    section_label: str,
    connector: str,
    query: str,
    fetched_at: str,
    bound_to: LineageBoundTo,
    detail: str = "",
) -> AnalyticsLineageRowOut:
    verified = bool(connector.strip() and query.strip() and fetched_at.strip())
    return AnalyticsLineageRowOut(
        section_id=section_id,
        section_label=section_label,
        connector=connector.strip(),
        connector_label=_connector_label(connector),
        query=query.strip(),
        fetched_at=fetched_at.strip(),
        bound_to=bound_to,
        verified=verified,
        detail=detail,
    )


def _rows_from_stored(structured: dict[str, Any]) -> list[AnalyticsLineageRowOut]:
    raw = structured.get("lineage_rows")
    if not isinstance(raw, list):
        return []
    rows: list[AnalyticsLineageRowOut] = []
    for idx, item in enumerate(raw[:32]):
        if not isinstance(item, dict):
            continue
        connector = str(item.get("connector") or "")
        query = str(item.get("query") or "")
        fetched_at = str(item.get("fetched_at") or item.get("timestamp") or "")
        rows.append(
            _lineage_row_from_parts(
                section_id=str(item.get("section_id") or f"stored-{idx + 1}"),
                section_label=str(item.get("section_label") or "Report section"),
                connector=connector,
                query=query,
                fetched_at=fetched_at,
                bound_to="stored",
                detail=str(item.get("detail") or ""),
            ),
        )
    return rows


def _rows_from_brief_structured(structured: dict[str, Any]) -> list[AnalyticsLineageRowOut]:
    rows: list[AnalyticsLineageRowOut] = []
    sources = structured.get("sources")
    date_range = structured.get("date_range")
    if not isinstance(sources, list):
        return rows
    range_label = ""
    fetched_at = ""
    if isinstance(date_range, dict):
        range_label = str(date_range.get("label") or "")
        fetched_at = str(date_range.get("end") or date_range.get("start") or "")
    for idx, source in enumerate(sources[:8]):
        slug = str(source).strip()
        if not slug:
            continue
        rows.append(
            _lineage_row_from_parts(
                section_id=f"brief-{slug}",
                section_label="Report brief scope",
                connector=slug,
                query=f"read-only fetch · {range_label}".strip(" ·"),
                fetched_at=fetched_at,
                bound_to="brief",
                detail="Derived from business question wizard sources + date range.",
            ),
        )
    return rows


def _rows_from_chart_blocks(structured: dict[str, Any]) -> list[AnalyticsLineageRowOut]:
    rows: list[AnalyticsLineageRowOut] = []
    for block in parse_chart_blocks(structured):
        connector, query, fetched_at = parse_source_citation(block.source_citation)
        detail = ""
        if not block.source_citation.strip():
            detail = "data_gap — add source citation (connector · query · timestamp)."
        rows.append(
            _lineage_row_from_parts(
                section_id=block.id,
                section_label=block.title,
                connector=connector,
                query=query or block.title,
                fetched_at=fetched_at,
                bound_to="chart",
                detail=detail,
            ),
        )
    return rows


def _rows_from_markdown_sections(markdown_body: str) -> list[AnalyticsLineageRowOut]:
    """Extract lineage from markdown headings with inline citation brackets."""

    rows: list[AnalyticsLineageRowOut] = []
    citation_pattern = re.compile(r"\[(?P<citation>[^\]]+)\]")
    for line in markdown_body.splitlines():
        heading = line.strip()
        if not heading.startswith("## "):
            continue
        label = heading.removeprefix("## ").strip()
        if not label:
            continue
        match = citation_pattern.search(line)
        if match is None:
            rows.append(
                _lineage_row_from_parts(
                    section_id=re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48] or "section",
                    section_label=label,
                    connector="",
                    query="",
                    fetched_at="",
                    bound_to="markdown_section",
                    detail="data_gap — narrative section missing inline lineage citation.",
                ),
            )
            continue
        connector, query, fetched_at = parse_source_citation(match.group("citation"))
        rows.append(
            _lineage_row_from_parts(
                section_id=re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:48] or "section",
                section_label=label,
                connector=connector,
                query=query or label,
                fetched_at=fetched_at,
                bound_to="markdown_section",
            ),
        )
    return rows


def build_lineage_rows_from_deliverable(row: TaskFinalDeliverable) -> list[AnalyticsLineageRowOut]:
    """Compose lineage rows from structured JSON, chart blocks, and markdown sections."""

    structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
    return build_lineage_rows_from_payload(markdown_body=row.markdown_body, structured=structured)


def build_lineage_rows_from_payload(
    *,
    markdown_body: str,
    structured: dict[str, Any],
) -> list[AnalyticsLineageRowOut]:
    """Compose lineage rows from markdown + structured payload (no ORM required)."""

    stored = _rows_from_stored(structured)
    if stored:
        return stored[:32]

    merged: list[AnalyticsLineageRowOut] = []
    seen: set[str] = set()
    for candidate in (
        *_rows_from_chart_blocks(structured),
        *_rows_from_markdown_sections(markdown_body),
        *_rows_from_brief_structured(structured),
    ):
        key = f"{candidate.bound_to}:{candidate.section_id}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(candidate)
    return merged[:32]


def lineage_rows_to_structured(rows: list[AnalyticsLineageRowOut]) -> list[dict[str, str | bool]]:
    """Persist lineage rows on deliverable structured JSON."""

    return [
        {
            "section_id": row.section_id,
            "section_label": row.section_label,
            "connector": row.connector,
            "query": row.query,
            "fetched_at": row.fetched_at,
            "bound_to": row.bound_to,
            "verified": row.verified,
            "detail": row.detail,
        }
        for row in rows
    ]


async def _resolve_analytics_row(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    task_id: uuid.UUID | None = None,
    deliverable_id: uuid.UUID | None = None,
) -> TaskFinalDeliverable | None:
    if deliverable_id is not None:
        candidate = await fetch_owned_deliverable(
            session,
            deliverable_id=deliverable_id,
            dashboard_user_id=dashboard_user_id,
        )
        if candidate is not None and is_analytics_deliverable(candidate):
            return candidate
        return None

    rows = await list_owned_deliverables(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=40,
        tag="analytics",
    )
    for candidate in rows:
        if not is_analytics_deliverable(candidate):
            continue
        if task_id is not None and candidate.source_task_id != task_id:
            continue
        return candidate
    return None


async def compose_analytics_data_lineage_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    task_id: uuid.UUID | None = None,
    deliverable_id: uuid.UUID | None = None,
) -> AnalyticsDataLineageSnapshotOut:
    """Return lineage strip rows for active analytics report artifact."""

    if not settings.analytics_data_lineage_enabled:
        return AnalyticsDataLineageSnapshotOut(
            enabled=False,
            has_rows=False,
            empty_hint="Data lineage strip disabled.",
        )

    row = await _resolve_analytics_row(
        session,
        dashboard_user_id=dashboard_user_id,
        task_id=task_id,
        deliverable_id=deliverable_id,
    )
    if row is None:
        return AnalyticsDataLineageSnapshotOut(
            enabled=True,
            has_rows=False,
            empty_hint=(
                "No lineage yet — dispatch a business question and wait for fetch bees to tag "
                "connector · query · timestamp on each chart block."
            ),
        )

    lineage_rows = build_lineage_rows_from_deliverable(row)
    verified_count = sum(1 for item in lineage_rows if item.verified)
    gap_count = len(lineage_rows) - verified_count
    _logger.info(
        "analytics_data_lineage.snapshot",
        agent_id="analytics_data_lineage",
        swarm_id=str(dashboard_user_id),
        deliverable_id=str(row.id),
        row_count=len(lineage_rows),
        verified_count=verified_count,
    )
    return AnalyticsDataLineageSnapshotOut(
        enabled=True,
        has_rows=len(lineage_rows) > 0,
        deliverable_id=str(row.id),
        deliverable_version=row.version,
        report_title=row.title,
        rows=lineage_rows,
        verified_count=verified_count,
        gap_count=gap_count,
    )


__all__ = [
    "AnalyticsDataLineageSnapshotOut",
    "AnalyticsLineageRowOut",
    "build_lineage_rows_from_deliverable",
    "build_lineage_rows_from_payload",
    "compose_analytics_data_lineage_snapshot",
    "lineage_rows_to_structured",
    "parse_source_citation",
]
