"""Operator session compliance report builders (HTML + Markdown)."""

from __future__ import annotations

import html
import json
import uuid
from datetime import datetime
from typing import Any


def _iso(value: object | None) -> str:
    if value is None:
        return "—"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_block(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_supervisor_session_report_markdown(
    *,
    session_id: uuid.UUID,
    session: dict[str, Any],
    audit_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    context_history: list[dict[str, Any]],
    generated_at: datetime,
) -> str:
    """Render a printable operator session report as Markdown."""

    lines = [
        "# Queenswarm Operator Session Report",
        "",
        f"- Generated: `{generated_at.isoformat()}`",
        f"- Session: `{session_id}`",
        f"- Goal: {session.get('goal', '')}",
        f"- Status: `{session.get('status', '')}`",
        f"- Runtime: `{session.get('runtime_mode', '')}`",
        "",
        "## Sub-agents",
        "",
    ]
    for sub in session.get("sub_agents") or []:
        if not isinstance(sub, dict):
            continue
        lines.append(
            f"- `{sub.get('role', '?')}` · `{sub.get('status', '?')}` · `{sub.get('runtime_mode', '?')}`",
        )
    lines.extend(["", "## Operator audit", ""])
    if not audit_rows:
        lines.append("_No operator audit rows._")
    else:
        for row in audit_rows:
            lines.append(
                f"- `{row.get('created_at', '')}` · `{row.get('action', '')}` · "
                f"`{json.dumps(row.get('payload') or {}, ensure_ascii=False, default=str)}`",
            )
    lines.extend(["", "## Context history", ""])
    if not context_history:
        lines.append("_No context diffs recorded._")
    else:
        for row in context_history:
            lines.append(
                f"- `{row.get('created_at', '')}` · `{row.get('action', '')}` · "
                f"`{json.dumps(row.get('context_diff') or {}, ensure_ascii=False, default=str)}`",
            )
    lines.extend(["", "## Session timeline", ""])
    if not event_rows:
        lines.append("_No timeline events._")
    else:
        for event in event_rows:
            lines.append(
                f"- `{event.get('occurred_at', '')}` · `{event.get('event_type', '')}` · "
                f"{event.get('message', '')}",
            )
    return "\n".join(lines) + "\n"


def build_supervisor_session_report_html(
    *,
    session_id: uuid.UUID,
    session: dict[str, Any],
    audit_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    context_history: list[dict[str, Any]],
    generated_at: datetime,
) -> str:
    """Render a browser-printable HTML operator session report."""

    goal = html.escape(str(session.get("goal") or ""))
    status = html.escape(str(session.get("status") or ""))
    runtime = html.escape(str(session.get("runtime_mode") or ""))
    sub_rows = []
    for sub in session.get("sub_agents") or []:
        if not isinstance(sub, dict):
            continue
        sub_rows.append(
            "<tr>"
            f"<td>{html.escape(str(sub.get('role', '')))}</td>"
            f"<td>{html.escape(str(sub.get('status', '')))}</td>"
            f"<td>{html.escape(str(sub.get('runtime_mode', '')))}</td>"
            "</tr>",
        )
    audit_items = "".join(
        "<li>"
        f"<code>{html.escape(_iso(row.get('created_at')))}</code> · "
        f"<strong>{html.escape(str(row.get('action', '')))}</strong> · "
        f"<pre>{html.escape(_json_block(row.get('payload') or {}))}</pre>"
        "</li>"
        for row in audit_rows
    ) or "<li><em>No operator audit rows.</em></li>"
    history_items = "".join(
        "<li>"
        f"<code>{html.escape(_iso(row.get('created_at')))}</code> · "
        f"<strong>{html.escape(str(row.get('action', '')))}</strong> · "
        f"<pre>{html.escape(_json_block(row.get('context_diff') or {}))}</pre>"
        "</li>"
        for row in context_history
    ) or "<li><em>No context diffs recorded.</em></li>"
    event_items = "".join(
        "<li>"
        f"<code>{html.escape(_iso(event.get('occurred_at')))}</code> · "
        f"<strong>{html.escape(str(event.get('event_type', '')))}</strong> · "
        f"{html.escape(str(event.get('message') or ''))}"
        "</li>"
        for event in event_rows
    ) or "<li><em>No timeline events.</em></li>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Session report {html.escape(str(session_id))}</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; background: #050510; color: #e4e4e7; padding: 2rem; }}
    h1, h2 {{ color: #ffb800; }}
    code, pre {{ font-family: ui-monospace, monospace; font-size: 12px; }}
    pre {{ background: #111827; padding: 0.75rem; border-radius: 0.5rem; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
    th, td {{ border: 1px solid #27272a; padding: 0.5rem; text-align: left; }}
    li {{ margin-bottom: 0.75rem; }}
  </style>
</head>
<body>
  <h1>Queenswarm Operator Session Report</h1>
  <p>Generated: <code>{html.escape(generated_at.isoformat())}</code></p>
  <p>Session: <code>{html.escape(str(session_id))}</code></p>
  <p><strong>Goal:</strong> {goal}</p>
  <p><strong>Status:</strong> {status} · <strong>Runtime:</strong> {runtime}</p>

  <h2>Sub-agents</h2>
  <table>
    <thead><tr><th>Role</th><th>Status</th><th>Runtime</th></tr></thead>
    <tbody>{''.join(sub_rows) or '<tr><td colspan="3"><em>None</em></td></tr>'}</tbody>
  </table>

  <h2>Operator audit</h2>
  <ul>{audit_items}</ul>

  <h2>Context history</h2>
  <ul>{history_items}</ul>

  <h2>Session timeline</h2>
  <ul>{event_items}</ul>
</body>
</html>
"""


def _pdf_safe_text(value: object, *, max_len: int = 4000) -> str:
    """Normalize text for built-in PDF fonts (Latin-1)."""

    raw = _iso(value) if value is not None else "—"
    clipped = raw if len(raw) <= max_len else f"{raw[: max_len - 3]}..."
    return clipped.encode("latin-1", errors="replace").decode("latin-1")


class _QueenswarmReportPDF:
    """Bee-hive branded PDF document with header band and cyan hex dividers."""

    def __init__(self) -> None:
        from fpdf import FPDF

        class _Doc(FPDF):
            def header(self) -> None:
                self.set_fill_color(5, 5, 16)
                self.rect(0, 0, self.w, 20, style="F")
                self.set_y(5)
                self.set_font("Helvetica", "B", 14)
                self.set_text_color(255, 184, 0)
                self.cell(0, 7, "Queenswarm Operator Session Report", align="C", new_x="LMARGIN", new_y="NEXT")
                self.set_text_color(35, 35, 48)
                self.ln(2)

            def footer(self) -> None:
                self.set_y(-12)
                self.set_font("Helvetica", "I", 8)
                self.set_text_color(120, 120, 130)
                self.cell(0, 6, f"Queenswarm | queenswarm.love | page {self.page_no()}", align="C")

        self._pdf = _Doc()
        self._pdf.set_auto_page_break(auto=True, margin=18)
        self._pdf.add_page()

    @property
    def epw(self) -> float:
        return float(self._pdf.epw)

    def meta_line(self, text: str) -> None:
        self._pdf.set_font("Helvetica", size=10)
        self._pdf.set_text_color(35, 35, 48)
        self._pdf.multi_cell(self.epw, 5.5, _pdf_safe_text(text))

    def section(self, title: str) -> None:
        pdf = self._pdf
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(255, 184, 0)
        pdf.cell(self.epw, 7, _pdf_safe_text(title), new_x="LMARGIN", new_y="NEXT")
        y = pdf.get_y()
        pdf.set_draw_color(0, 255, 255)
        pdf.set_line_width(0.45)
        pdf.line(pdf.l_margin, y, pdf.l_margin + self.epw, y)
        cx = pdf.l_margin + self.epw / 2
        pdf.set_fill_color(0, 255, 255)
        for dx in (-3.5, 0, 3.5):
            pdf.rect(cx + dx - 0.6, y - 0.6, 1.2, 1.2, style="F")
        pdf.ln(3)
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(35, 35, 48)

    def body_line(self, text: str, *, max_len: int = 1200) -> None:
        self._pdf.multi_cell(self.epw, 5, _pdf_safe_text(text, max_len=max_len))

    def render(self) -> bytes:
        return bytes(self._pdf.output())


def build_supervisor_session_report_pdf(
    *,
    session_id: uuid.UUID,
    session: dict[str, Any],
    audit_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    context_history: list[dict[str, Any]],
    generated_at: datetime,
) -> bytes:
    """Render an operator session report as a downloadable PDF byte stream."""

    doc = _QueenswarmReportPDF()
    doc.meta_line(f"Generated: {generated_at.isoformat()}")
    doc.meta_line(f"Session: {session_id}")
    doc.meta_line(f"Goal: {session.get('goal', '')}")
    doc.meta_line(f"Status: {session.get('status', '')} | Runtime: {session.get('runtime_mode', '')}")

    doc.section("Sub-agents")
    subs = session.get("sub_agents") or []
    if not subs:
        doc.body_line("None")
    else:
        for sub in subs:
            if not isinstance(sub, dict):
                continue
            doc.body_line(
                f"- {sub.get('role', '?')} | {sub.get('status', '?')} | {sub.get('runtime_mode', '?')}",
            )

    doc.section("Operator audit")
    if not audit_rows:
        doc.body_line("No operator audit rows.")
    else:
        for row in audit_rows:
            doc.body_line(
                f"- {_iso(row.get('created_at'))} | {row.get('action', '')} | "
                f"{_json_block(row.get('payload') or {})}",
            )

    doc.section("Context history")
    if not context_history:
        doc.body_line("No context diffs recorded.")
    else:
        for row in context_history:
            doc.body_line(
                f"- {_iso(row.get('created_at'))} | {row.get('action', '')} | "
                f"{_json_block(row.get('context_diff') or {})}",
            )

    doc.section("Session timeline")
    if not event_rows:
        doc.body_line("No timeline events.")
    else:
        for event in event_rows:
            doc.body_line(
                f"- {_iso(event.get('occurred_at'))} | {event.get('event_type', '')} | "
                f"{event.get('message', '')}",
                max_len=800,
            )

    return doc.render()


__all__ = [
    "build_supervisor_session_report_html",
    "build_supervisor_session_report_markdown",
    "build_supervisor_session_report_pdf",
]
