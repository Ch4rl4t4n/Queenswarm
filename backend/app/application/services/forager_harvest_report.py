"""Operator-facing forager harvest report builders (HTML, Markdown, PDF)."""

from __future__ import annotations

import html
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.session_report import _html_to_pdf_bytes
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    """Remove emoji that DejaVu cannot embed in PDF streams."""

    cleaned = _EMOJI_RE.sub("", text)
    return cleaned.replace("✅", "[OK]").replace("❌", "[X]").replace("⚠️", "[!]")


def _iso(value: object | None) -> str:
    if value is None:
        return "—"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _html_heading(text: str, *, level: int = 2) -> str:
    size = {1: 16, 2: 13, 3: 11}.get(level, 11)
    tag = f"h{level}"
    label = html.escape(_strip_emoji(text))
    return (
        f'<{tag}><font face="DejaVu" color="#b8860b" size="{size}">'
        f"<b>{label}</b></font></{tag}>"
    )


def _html_text_block(text: str, *, size: int = 10, bold: bool = False) -> str:
    safe = _strip_emoji(text)
    escaped = html.escape(safe).replace("\n", "<br/>")
    inner = f"<b>{escaped}</b>" if bold else escaped
    return f'<p style="line-height:1.45"><font face="DejaVu" size="{size}">{inner}</font></p>'


def _finding_title(content_text: str, source_url: str | None) -> str:
    first_line = content_text.strip().splitlines()[0].strip() if content_text.strip() else ""
    title = re.sub(r"^#+\s*", "", first_line).strip()
    if len(title) >= 12:
        return title[:140]
    if source_url:
        return source_url.rsplit("/", maxsplit=1)[-1][:140] or "Harvested signal"
    return "Harvested signal"


def _executive_summary(*, forager: dict[str, Any], items: list[dict[str, Any]]) -> str:
    """Compose a readable operator summary without LLM cost."""

    name = str(forager.get("name") or "Forager")
    source_type = str(forager.get("source_type") or "unknown")
    description = str(forager.get("description") or "").strip()
    total = int(forager.get("items_total") or len(items))

    parts: list[str] = []
    if description:
        parts.append(description)
    parts.append(
        f"Intelligence report for **{name}** ({source_type}). "
        f"The hive indexed **{total}** signal{'s' if total != 1 else ''} tagged to this forager.",
    )
    if items:
        snippets: list[str] = []
        for row in items[:3]:
            body = str(row.get("body") or "").strip()
            if not body:
                continue
            line = body.splitlines()[0].strip()
            line = re.sub(r"^#+\s*", "", line)
            if len(line) > 180:
                line = f"{line[:177]}…"
            if line:
                snippets.append(line)
        if snippets:
            parts.append("Recent highlights:\n" + "\n".join(f"• {snippet}" for snippet in snippets))
    else:
        parts.append("No harvested items yet — run the forager or verify source configuration.")
    return "\n\n".join(parts)


async def load_forager_harvest_report(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    item_limit: int = 25,
) -> dict[str, Any] | None:
    """Load forager metadata and newest knowledge rows for report rendering."""

    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return None

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
        .limit(max(1, min(item_limit, 50)))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    items = [
        {
            "title": _finding_title(str(row.content_text or ""), row.source_url),
            "body": str(row.content_text or "").strip(),
            "source_url": row.source_url,
            "scraped_at": row.scraped_at,
            "confidence": float(row.confidence_score or 0.0),
            "source_type": str(row.source_type or ""),
        }
        for row in rows
    ]

    return {
        "forager_id": str(forager.id),
        "name": forager.name,
        "description": forager.description or "",
        "source_type": forager.source_type,
        "items_total": items_total,
        "items": items,
        "generated_at": datetime.now(tz=UTC),
        "executive_summary": _executive_summary(
            forager={
                "name": forager.name,
                "description": forager.description,
                "source_type": forager.source_type,
                "items_total": items_total,
            },
            items=items,
        ),
    }


def build_forager_harvest_report_markdown(report: dict[str, Any]) -> str:
    """Render operator harvest report as Markdown."""

    name = str(report.get("name") or "Forager")
    lines = [
        f"# Forager Intelligence Report · {name}",
        "",
        f"- Generated: `{_iso(report.get('generated_at'))}`",
        f"- Forager: `{report.get('forager_id', '')}`",
        f"- Source type: `{report.get('source_type', '')}`",
        f"- Indexed signals: **{report.get('items_total', 0)}**",
        "",
        "## Executive summary",
        "",
        str(report.get("executive_summary") or "").strip(),
        "",
        "## Key findings",
        "",
    ]
    items = list(report.get("items") or [])
    if not items:
        lines.append("_No harvested items in HiveMind yet._")
    else:
        for index, row in enumerate(items, start=1):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or f"Finding {index}")
            body = str(row.get("body") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            lines.extend(
                [
                    f"### {index}. {title}",
                    "",
                    f"- Scraped: `{_iso(row.get('scraped_at'))}`",
                    f"- Confidence: `{row.get('confidence', 0)}`",
                ],
            )
            if source_url:
                lines.append(f"- Source: {source_url}")
            lines.extend(["", body or "_Empty content._", ""])
    lines.extend(
        [
            "---",
            "",
            "Queenswarm · queenswarm.love · forager intelligence report",
            "",
        ],
    )
    return "\n".join(lines)


def build_forager_harvest_report_print_html(report: dict[str, Any]) -> str:
    """Print-optimized HTML for PDF export."""

    name = str(report.get("name") or "Forager")
    parts: list[str] = [
        _html_heading(f"Forager Intelligence Report · {name}", level=1),
        _html_text_block(
            f"Generated: {_iso(report.get('generated_at'))}  ·  "
            f"Source: {report.get('source_type', '')}  ·  "
            f"Signals indexed: {report.get('items_total', 0)}",
            size=9,
        ),
        _html_heading("Executive summary", level=2),
        _html_text_block(str(report.get("executive_summary") or ""), size=10),
        _html_heading("Key findings", level=2),
    ]
    items = list(report.get("items") or [])
    if not items:
        parts.append(_html_text_block("No harvested items in HiveMind yet."))
    else:
        for index, row in enumerate(items, start=1):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or f"Finding {index}")
            body = str(row.get("body") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            meta = (
                f"Scraped {_iso(row.get('scraped_at'))} · "
                f"Confidence {row.get('confidence', 0)}"
            )
            if source_url:
                meta += f" · {source_url}"
            parts.append(_html_heading(f"{index}. {title}", level=3))
            parts.append(_html_text_block(meta, size=8))
            parts.append(
                '<div style="margin:0 0 12px 0;padding:10px 12px;background-color:#f4f4f8;'
                'border-left:3px solid #ffb800">',
            )
            parts.append(_html_text_block(body or "Empty content.", size=9))
            parts.append("</div>")
    parts.append(
        '<p align="center"><font face="DejaVu" size="8" color="#888888">'
        "Queenswarm · queenswarm.love · forager intelligence report"
        "</font></p>",
    )
    return "\n".join(parts)


def build_forager_harvest_report_pdf(report: dict[str, Any]) -> bytes:
    """Render harvest report as downloadable PDF bytes."""

    return _html_to_pdf_bytes(build_forager_harvest_report_print_html(report))


__all__ = [
    "build_forager_harvest_report_markdown",
    "build_forager_harvest_report_pdf",
    "build_forager_harvest_report_print_html",
    "load_forager_harvest_report",
]
