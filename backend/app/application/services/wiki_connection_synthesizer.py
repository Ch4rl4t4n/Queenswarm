"""Compile Maps of Content + connection intelligence from capture notes."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.application.services.second_brain_capture import is_capture_note, parse_capture_fields
from app.infrastructure.persistence.models.knowledge import KnowledgeItem

_MIN_SHARED_TAGS = 2
_MAX_MOC_TOPICS = 12
_MAX_CONNECTIONS = 20


def _item_title(row: KnowledgeItem) -> str:
    fields = parse_capture_fields(row.content_text or "")
    idea = str(fields.get("idea") or "").strip()
    if idea:
        return idea[:120]
    preview = (row.content_text or "").replace("\n", " ").strip()
    return preview[:80] or str(row.id)[:8]


def _tag_buckets(rows: list[KnowledgeItem]) -> dict[str, list[KnowledgeItem]]:
    buckets: dict[str, list[KnowledgeItem]] = defaultdict(list)
    for row in rows:
        for tag in row.topic_tags or []:
            text = str(tag).strip().lower()
            if not text or text.startswith("connects:") or text == "second_brain:capture":
                continue
            buckets[text].append(row)
    return buckets


def _shared_tag_pairs(rows: list[KnowledgeItem]) -> list[tuple[KnowledgeItem, KnowledgeItem, list[str]]]:
    pairs: list[tuple[KnowledgeItem, KnowledgeItem, list[str]]] = []
    for index, left in enumerate(rows):
        left_tags = {str(t).lower() for t in (left.topic_tags or [])}
        for right in rows[index + 1 :]:
            right_tags = {str(t).lower() for t in (right.topic_tags or [])}
            shared = sorted(left_tags & right_tags - {"second_brain:capture", "wiki_layer:raw"})
            if len(shared) >= _MIN_SHARED_TAGS:
                pairs.append((left, right, shared))
    pairs.sort(key=lambda item: (-len(item[2]), _item_title(item[0])))
    return pairs[:_MAX_CONNECTIONS]


def compile_maps_of_content(rows: list[KnowledgeItem]) -> str:
    """Build MOC markdown grouped by topic tags and explicit CONNECTS TO links."""

    captures = [row for row in rows if is_capture_note(row.content_text or "")]
    if not captures:
        return "_No capture notes yet — use **Quick capture** on Wiki Layer to seed this map._"

    lines = [
        "# Maps of Content",
        "",
        "Navigation layer over second-brain captures. Gardener refreshes this from raw notes.",
        "",
        "## By topic",
    ]
    buckets = _tag_buckets(captures)
    ranked = sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0]))[:_MAX_MOC_TOPICS]
    if not ranked:
        lines.append("_No topic tags yet — add tags via Research Bee or capture connects._")
    else:
        for tag, items in ranked:
            lines.append(f"### {tag}")
            for row in items[:8]:
                lines.append(f"- {_item_title(row)} `({str(row.id)[:8]})`")
            lines.append("")

    explicit: list[str] = []
    for row in captures:
        fields = parse_capture_fields(row.content_text or "")
        idea = _item_title(row)
        for target in fields.get("connects_to") or []:
            explicit.append(f"- **{idea}** → {target}")
    lines.extend(["## Explicit links (CONNECTS TO)", ""])
    if explicit:
        lines.extend(explicit[:24])
    else:
        lines.append("_Add CONNECTS TO wikilinks in capture notes to surface intent here._")
    lines.append("")
    return "\n".join(lines)


def compile_connection_intelligence(rows: list[KnowledgeItem]) -> str:
    """Surface non-obvious links: shared tags, tensions, and cross-capture bridges."""

    captures = [row for row in rows if is_capture_note(row.content_text or "")]
    if len(captures) < 2:
        return "_Need at least two capture notes for connection intelligence._"

    lines = [
        "# Connection intelligence",
        "",
        "Auto-synthesized bridges across your vault (tag overlap + capture metadata).",
        "",
        "## Shared-topic bridges",
    ]
    pairs = _shared_tag_pairs(captures)
    if not pairs:
        lines.append("_No strong tag overlap yet — link captures with shared `connects:` or topic tags._")
    else:
        for left, right, shared in pairs:
            lines.append(
                f"- **{_item_title(left)}** ↔ **{_item_title(right)}** — shared: {', '.join(shared[:5])}",
            )

    tensions = []
    for row in captures:
        fields = parse_capture_fields(row.content_text or "")
        tension = str(fields.get("key_tension") or "").strip()
        if tension and not tension.startswith("_("):
            tensions.append(f"- **{_item_title(row)}** — {tension[:200]}")
    lines.extend(["", "## Key tensions (review weekly)", ""])
    if tensions:
        lines.extend(tensions[:12])
    else:
        lines.append("_Fill **Key Tension** in captures to compound insights over time._")

    use_cases: list[str] = []
    for row in captures:
        fields = parse_capture_fields(row.content_text or "")
        use_for = str(fields.get("might_use_for") or "").strip()
        if use_for and not use_for.startswith("_("):
            use_cases.append(f"- {_item_title(row)} → {use_for[:160]}")
    lines.extend(["", "## Actionable threads (MIGHT USE FOR)", ""])
    if use_cases:
        lines.extend(use_cases[:12])
    else:
        lines.append("_Add MIGHT USE FOR lines when capturing — Gardener surfaces actionable threads here._")
    lines.append("")
    return "\n".join(lines)


__all__ = ["compile_connection_intelligence", "compile_maps_of_content"]
