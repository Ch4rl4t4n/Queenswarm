"""DG5 — Export lane: approved structured rows → CSV / Notion / Sheet."""

from __future__ import annotations

import csv
import io
import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_structured_extract_service import (
    extract_schema_from_forager,
    knowledge_item_to_structured_row,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

_logger = get_logger(__name__)

ExportDestination = Literal["csv", "notion", "sheet"]
ExportMode = Literal["simulate", "live"]

_EXPORT_APPROVED_TAG = "export-approved"


class ForagerExportLaneSnapshotOut(BaseModel):
    """Operator snapshot for export lane destinations."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    destinations: list[str]
    notion_configured: bool
    default_mode: ExportMode
    operator_hint: str


class ForagerExportPreviewOut(BaseModel):
    """Simulate-first preview before export."""

    model_config = ConfigDict(extra="forbid")

    forager_id: str
    forager_name: str
    extract_schema: str
    destination: ExportDestination
    mode: ExportMode
    row_count: int
    columns: list[str]
    preview_rows: list[dict[str, Any]]
    notion_payloads: list[dict[str, Any]] = Field(default_factory=list)
    csv_preview: str = ""
    operator_hint: str = ""


class ForagerExportSubmitOut(BaseModel):
    """Export lane result."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    forager_id: str
    destination: ExportDestination
    mode: ExportMode
    row_count: int
    simulated: bool
    message: str
    csv_content: str | None = None
    notion_results: list[dict[str, Any]] = Field(default_factory=list)
    approved_tagged: int = 0


def compose_export_lane_snapshot() -> ForagerExportLaneSnapshotOut:
    """Static export lane capabilities for UI."""

    enabled = bool(settings.forager_export_lane_enabled)
    return ForagerExportLaneSnapshotOut(
        enabled=enabled,
        destinations=["csv", "notion", "sheet"],
        notion_configured=False,
        default_mode="simulate",
        operator_hint=(
            "Export structured forager rows — simulate-first for Notion/Sheet; CSV downloads immediately."
        ),
    )


async def compose_export_lane_snapshot_async(session: AsyncSession) -> ForagerExportLaneSnapshotOut:
    """Snapshot with live Notion connector probe."""

    snap = compose_export_lane_snapshot()
    if not snap.enabled:
        return snap
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug="notion_workspace")
    notion_ok = row is not None and bool(row.is_active)
    return ForagerExportLaneSnapshotOut(
        enabled=snap.enabled,
        destinations=list(snap.destinations),
        notion_configured=notion_ok,
        default_mode=snap.default_mode,
        operator_hint=snap.operator_hint,
    )


async def _load_export_knowledge_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    knowledge_ids: list[uuid.UUID] | None,
    approved_only: bool,
    limit: int,
) -> tuple[ForagerORM | None, list[KnowledgeItem]]:
    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return None, []

    tag = f"forager:{forager.id}"
    stmt = (
        select(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
        )
        .order_by(desc(KnowledgeItem.scraped_at))
        .limit(max(1, min(limit, 100)))
    )
    if knowledge_ids:
        stmt = stmt.where(KnowledgeItem.id.in_(knowledge_ids))
    rows = list((await session.execute(stmt)).scalars().all())
    if approved_only and not knowledge_ids:
        rows = [row for row in rows if _EXPORT_APPROVED_TAG in list(row.topic_tags or [])]
    return forager, rows


def _flatten_rows(
    structured: list[tuple[KnowledgeItem, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    flat: list[dict[str, Any]] = []
    columns: list[str] = []
    for item, row in structured:
        merged = {
            "knowledge_id": str(item.id),
            "scraped_at": item.scraped_at.isoformat() if item.scraped_at else "",
            "source_url": item.source_url or "",
            **{k: str(v or "") for k, v in row.items()},
        }
        flat.append(merged)
        for key in merged:
            if key not in columns:
                columns.append(key)
    return flat, columns


async def _collect_flat_export_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    knowledge_ids: list[uuid.UUID] | None,
    approved_only: bool,
    limit: int,
) -> tuple[ForagerORM | None, list[dict[str, Any]], list[str], str]:
    """Load forager knowledge and flatten structured rows for export."""

    forager, knowledge_rows = await _load_export_knowledge_rows(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        knowledge_ids=knowledge_ids,
        approved_only=approved_only,
        limit=limit,
    )
    if forager is None:
        return None, [], [], "general"

    schema = extract_schema_from_forager(forager)
    structured: list[tuple[KnowledgeItem, dict[str, Any]]] = []
    for item in knowledge_rows:
        parsed = knowledge_item_to_structured_row(item, extract_schema=schema)
        if parsed is not None:
            structured.append((item, parsed.row))
    flat_rows, columns = _flatten_rows(structured)
    return forager, flat_rows, columns, schema


def _rows_to_csv(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def _notion_page_payload(database_id: str, flat_row: dict[str, Any]) -> dict[str, Any]:
    """Build Notion create_page body (simulate-first)."""

    title_val = (
        flat_row.get("title")
        or flat_row.get("name")
        or flat_row.get("product")
        or flat_row.get("knowledge_id")
        or "Goldmine row"
    )
    properties: dict[str, Any] = {
        "Name": {"title": [{"text": {"content": str(title_val)[:2000]}}]},
    }
    for key, val in flat_row.items():
        if key in {"knowledge_id", "title", "name", "product"} or not val:
            continue
        prop_key = key.replace("_", " ").title()[:100]
        properties[prop_key] = {"rich_text": [{"text": {"content": str(val)[:2000]}}]}
    return {
        "parent": {"database_id": database_id},
        "properties": properties,
    }


async def approve_forager_export_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    knowledge_ids: list[uuid.UUID],
) -> int:
    """Tag knowledge rows as operator-approved for export."""

    if not knowledge_ids:
        return 0
    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return 0

    tag = f"forager:{forager.id}"
    stmt = select(KnowledgeItem).where(
        KnowledgeItem.tenant_id == tenant_id,
        KnowledgeItem.id.in_(knowledge_ids),
        KnowledgeItem.topic_tags.contains([tag]),
    )
    rows = list((await session.execute(stmt)).scalars().all())
    tagged = 0
    for row in rows:
        tags = list(row.topic_tags or [])
        if _EXPORT_APPROVED_TAG not in tags:
            tags.append(_EXPORT_APPROVED_TAG)
            row.topic_tags = tags[:32]
            tagged += 1
    await session.flush()
    return tagged


async def preview_forager_export(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    destination: ExportDestination,
    mode: ExportMode = "simulate",
    knowledge_ids: list[uuid.UUID] | None = None,
    approved_only: bool = True,
    notion_database_id: str | None = None,
    limit: int = 50,
) -> ForagerExportPreviewOut | None:
    """Build simulate-first export preview."""

    if not settings.forager_export_lane_enabled:
        raise ValueError("forager_export_lane_disabled")

    forager, flat_rows, columns, schema = await _collect_flat_export_rows(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        knowledge_ids=knowledge_ids,
        approved_only=approved_only,
        limit=limit,
    )
    if forager is None:
        return None

    csv_text = _rows_to_csv(flat_rows, columns)

    notion_payloads: list[dict[str, Any]] = []
    if destination == "notion" and notion_database_id and flat_rows:
        notion_payloads = [_notion_page_payload(notion_database_id, row) for row in flat_rows[:25]]

    hint = (
        "No approved rows — approve structured hits for export or disable approved-only."
        if not flat_rows and approved_only
        else f"Simulate-first — {len(flat_rows)} row(s) ready for {destination}."
    )

    return ForagerExportPreviewOut(
        forager_id=str(forager.id),
        forager_name=forager.name,
        extract_schema=schema,
        destination=destination,
        mode=mode,
        row_count=len(flat_rows),
        columns=columns,
        preview_rows=flat_rows[:12],
        notion_payloads=notion_payloads[:5],
        csv_preview=csv_text[:4000],
        operator_hint=hint,
    )


async def submit_forager_export(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    destination: ExportDestination,
    mode: ExportMode = "simulate",
    knowledge_ids: list[uuid.UUID] | None = None,
    approved_only: bool = True,
    notion_database_id: str | None = None,
    dashboard_user_id: uuid.UUID | None = None,
    operator_confirmed: bool = False,
    limit: int = 50,
) -> ForagerExportSubmitOut | None:
    """Execute export lane — CSV immediate; Notion/Sheet simulate-first."""

    preview = await preview_forager_export(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        destination=destination,
        mode=mode,
        knowledge_ids=knowledge_ids,
        approved_only=approved_only,
        notion_database_id=notion_database_id,
        limit=limit,
    )
    if preview is None:
        return None

    if preview.row_count == 0:
        return ForagerExportSubmitOut(
            ok=False,
            forager_id=preview.forager_id,
            destination=destination,
            mode=mode,
            row_count=0,
            simulated=True,
            message=preview.operator_hint,
        )

    forager, flat_rows, columns, schema = await _collect_flat_export_rows(
        session,
        tenant_id=tenant_id,
        forager_id=forager_id,
        knowledge_ids=knowledge_ids,
        approved_only=approved_only,
        limit=limit,
    )
    if forager is None:
        return None

    csv_content: str | None = None
    if destination in {"csv", "sheet"}:
        csv_content = _rows_to_csv(flat_rows, columns)

    notion_results: list[dict[str, Any]] = []
    simulated = mode == "simulate" or destination in {"csv", "sheet"}

    if destination == "notion" and notion_database_id:
        payloads = [_notion_page_payload(notion_database_id, row) for row in flat_rows[:25]]
        if mode == "live" and operator_confirmed and dashboard_user_id is not None:
            from app.application.services.execution_studio import execute_studio_tool
            from app.infrastructure.persistence.models.tenant import Tenant

            tenant = await session.get(Tenant, tenant_id)
            for payload in payloads[:25]:
                result = await execute_studio_tool(
                    session,
                    dashboard_user_id=dashboard_user_id,
                    tenant=tenant,
                    connector_slug="notion_workspace",
                    tool_name="create_page",
                    arguments=payload,
                    mode="live",
                    manager_slug="content_creation",
                    operator_confirmed=True,
                )
                notion_results.append(result)
            simulated = False
        else:
            for payload in payloads[:25]:
                notion_results.append(
                    {
                        "ok": True,
                        "mode": "simulate",
                        "executed": False,
                        "preview": {
                            "connector_slug": "notion_workspace",
                            "tool_name": "create_page",
                            "arguments": payload,
                        },
                    },
                )
            simulated = True

    approved_tagged = 0
    if knowledge_ids:
        approved_tagged = await approve_forager_export_rows(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            knowledge_ids=knowledge_ids,
        )

    _logger.info(
        "forager.export_lane_submit",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        forager_id=preview.forager_id,
        destination=destination,
        mode=mode,
        row_count=preview.row_count,
        simulated=simulated,
    )

    dest_label = "Google Sheet (CSV)" if destination == "sheet" else destination.upper()
    return ForagerExportSubmitOut(
        ok=True,
        forager_id=preview.forager_id,
        destination=destination,
        mode=mode if not simulated else "simulate",
        row_count=preview.row_count,
        simulated=simulated,
        message=f"Exported {preview.row_count} row(s) to {dest_label} ({'simulate' if simulated else 'live'}).",
        csv_content=csv_content,
        notion_results=notion_results,
        approved_tagged=approved_tagged,
    )


__all__ = [
    "approve_forager_export_rows",
    "compose_export_lane_snapshot",
    "compose_export_lane_snapshot_async",
    "preview_forager_export",
    "submit_forager_export",
    "ForagerExportLaneSnapshotOut",
    "ForagerExportPreviewOut",
    "ForagerExportSubmitOut",
]
