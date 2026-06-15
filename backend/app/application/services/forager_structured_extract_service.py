"""Forager structured extract orchestration (DG2)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.domain.forager.extract_templates import (
    embed_structured_payload,
    heuristic_structured_row,
    normalize_extract_schema,
    parse_structured_payload,
    validate_structured_row,
)
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

_logger = get_logger(__name__)

_STRUCTURED_TAG_PREFIX = "structured-extract:"


class ForagerStructuredRowOut(BaseModel):
    """One validated structured row from HiveMind."""

    model_config = ConfigDict(extra="forbid")

    knowledge_id: str
    extract_schema: str
    scraped_at: datetime | None = None
    source_url: str | None = None
    row: dict[str, Any]


class ForagerStructuredRowsOut(BaseModel):
    """Structured extract table for one forager."""

    model_config = ConfigDict(extra="forbid")

    forager_id: str
    forager_name: str
    extract_schema: str
    enabled: bool
    rows: list[ForagerStructuredRowOut]
    total_structured: int
    items_total: int


def extract_schema_from_forager(forager: ForagerORM) -> str:
    """Read extract schema from forager filter_config."""

    cfg = dict(forager.filter_config or {})
    return normalize_extract_schema(str(cfg.get("extract_schema") or cfg.get("monitor_niche") or "general"))


def normalize_ingest_record_for_schema(
    record: dict[str, Any],
    *,
    extract_schema: str,
) -> dict[str, Any]:
    """Enrich ingest record with embedded structured JSON when enabled."""

    if not settings.forager_structured_extract_enabled:
        return record

    schema = normalize_extract_schema(extract_schema)
    content_text = str(record.get("content_text") or "").strip()
    if not content_text:
        return record

    existing = record.get("structured_row")
    if isinstance(existing, dict):
        structured = validate_structured_row(schema, existing) or existing
    else:
        embedded = parse_structured_payload(content_text)
        if embedded is not None:
            structured = validate_structured_row(schema, embedded)
        else:
            structured = heuristic_structured_row(
                schema=schema,  # type: ignore[arg-type]
                content_text=content_text,
                source_url=str(record.get("source_url") or "").strip() or None,
            )
            structured = validate_structured_row(schema, structured) or structured

    out = dict(record)
    out["content_text"] = embed_structured_payload(content_text, structured)
    tags = [str(tag).strip() for tag in list(out.get("topic_tags") or []) if str(tag).strip()]
    schema_tag = f"{_STRUCTURED_TAG_PREFIX}{schema}"
    out["topic_tags"] = list(dict.fromkeys([*tags, schema_tag, "structured-extract"]))[:32]
    return out


def knowledge_item_to_structured_row(
    item: KnowledgeItem,
    *,
    extract_schema: str,
) -> ForagerStructuredRowOut | None:
    """Parse one knowledge row into a validated structured output."""

    schema = normalize_extract_schema(extract_schema)
    embedded = parse_structured_payload(str(item.content_text or ""))
    if embedded is None:
        embedded = heuristic_structured_row(
            schema=schema,  # type: ignore[arg-type]
            content_text=str(item.content_text or ""),
            source_url=item.source_url,
        )
    validated = validate_structured_row(schema, embedded)
    if validated is None:
        return None
    return ForagerStructuredRowOut(
        knowledge_id=str(item.id),
        extract_schema=schema,
        scraped_at=item.scraped_at,
        source_url=item.source_url,
        row=validated,
    )


async def list_forager_structured_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    limit: int = 25,
) -> ForagerStructuredRowsOut | None:
    """Load structured rows for one forager."""

    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return None

    schema = extract_schema_from_forager(forager)
    tag = f"forager:{forager.id}"
    count_stmt = (
        select(func.count())
        .select_from(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
        )
    )
    items_total = int((await session.scalar(count_stmt)) or 0)

    stmt = (
        select(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
        )
        .order_by(desc(KnowledgeItem.scraped_at))
        .limit(max(1, min(limit, 50)))
    )
    knowledge_rows = list((await session.execute(stmt)).scalars().all())

    rows: list[ForagerStructuredRowOut] = []
    for item in knowledge_rows:
        parsed = knowledge_item_to_structured_row(item, extract_schema=schema)
        if parsed is not None:
            rows.append(parsed)

    return ForagerStructuredRowsOut(
        forager_id=str(forager.id),
        forager_name=forager.name,
        extract_schema=schema,
        enabled=bool(settings.forager_structured_extract_enabled),
        rows=rows,
        total_structured=len(rows),
        items_total=items_total,
    )


__all__ = [
    "ForagerStructuredRowOut",
    "ForagerStructuredRowsOut",
    "extract_schema_from_forager",
    "knowledge_item_to_structured_row",
    "list_forager_structured_rows",
    "normalize_ingest_record_for_schema",
]
