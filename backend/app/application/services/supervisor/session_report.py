"""Operator session compliance report builders (HTML + Markdown)."""

from __future__ import annotations

import html
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]",
    flags=re.UNICODE,
)


def _iso(value: object | None) -> str:
    if value is None:
        return "—"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _json_block(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _session_goal(session: dict[str, Any]) -> str:
    """Prefer operator raw goal from context_summary over mission-wrapped session.goal."""

    ctx = session.get("context_summary")
    if isinstance(ctx, dict):
        raw_goal = ctx.get("raw_goal")
        if isinstance(raw_goal, str) and raw_goal.strip():
            return raw_goal.strip()
    return str(session.get("goal") or "")


def _sub_agent_output_rows(session: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Return (role, status, last_output) for sub-agents that produced text."""

    rows: list[tuple[str, str, str]] = []
    for sub in session.get("sub_agents") or []:
        if not isinstance(sub, dict):
            continue
        output = str(sub.get("last_output") or "").strip()
        if not output:
            continue
        rows.append((str(sub.get("role", "?")), str(sub.get("status", "?")), output))
    return rows


def _strip_emoji(text: str) -> str:
    """Remove emoji that DejaVu cannot embed in PDF streams."""

    cleaned = _EMOJI_RE.sub("", text)
    return cleaned.replace("✅", "[OK]").replace("❌", "[X]").replace("⚠️", "[!]")


def _html_text_block(text: str, *, size: int = 10, bold: bool = False) -> str:
    """Render escaped multiline text for fpdf write_html (DejaVu, UTF-8 safe)."""

    safe = _strip_emoji(text)
    escaped = html.escape(safe).replace("\n", "<br/>")
    inner = f"<b>{escaped}</b>" if bold else escaped
    return f'<p style="line-height:1.45"><font face="DejaVu" size="{size}">{inner}</font></p>'


def _html_heading(text: str, *, level: int = 2) -> str:
    """Amber section heading for print/PDF layout."""

    size = {1: 16, 2: 13, 3: 11}.get(level, 11)
    tag = f"h{level}"
    label = html.escape(text)
    return (
        f'<{tag}><font face="DejaVu" color="#b8860b" size="{size}">'
        f"<b>{label}</b></font></{tag}>"
    )


def build_supervisor_session_report_print_html(
    *,
    session_id: uuid.UUID,
    session: dict[str, Any],
    audit_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    context_history: list[dict[str, Any]],
    generated_at: datetime,
) -> str:
    """Print-optimized HTML (white paper, readable in Chrome PDF viewer)."""

    goal = _session_goal(session)
    parts: list[str] = [
        _html_heading("Queenswarm Operator Session Report", level=1),
        _html_text_block(f"Generated: {generated_at.isoformat()}", size=9),
        _html_text_block(f"Session: {session_id}", size=9),
        _html_text_block(
            f"Status: {session.get('status', '')}  ·  Runtime: {session.get('runtime_mode', '')}",
            size=9,
        ),
        _html_heading("Mission goal", level=2),
        _html_text_block(goal, size=10),
    ]
    error_text = str(session.get("error_text") or "").strip()
    if error_text:
        parts.append(_html_text_block(f"Error: {error_text}", size=10, bold=True))

    parts.append(_html_heading("Sub-agents", level=2))
    subs = session.get("sub_agents") or []
    if not subs:
        parts.append(_html_text_block("None"))
    else:
        for sub in subs:
            if not isinstance(sub, dict):
                continue
            parts.append(
                _html_text_block(
                    f"• {sub.get('role', '?')} — {sub.get('status', '?')} ({sub.get('runtime_mode', '?')})",
                    size=10,
                ),
            )

    parts.append(_html_heading("Deliverables", level=2))
    output_rows = _sub_agent_output_rows(session)
    if not output_rows:
        parts.append(_html_text_block("No sub-agent outputs recorded yet."))
    else:
        for role, status, output in output_rows:
            parts.append(_html_heading(f"{role} · {status}", level=3))
            parts.append(
                '<div style="margin:0 0 12px 0;padding:10px 12px;background-color:#f4f4f8;'
                'border-left:3px solid #00ffff">',
            )
            parts.append(_html_text_block(output, size=9))
            parts.append("</div>")

    parts.append(_html_heading("Operator audit", level=2))
    if not audit_rows:
        parts.append(_html_text_block("No operator audit rows."))
    else:
        for row in audit_rows:
            parts.append(
                _html_text_block(
                    f"• {_iso(row.get('created_at'))} — {row.get('action', '')}\n"
                    f"{_json_block(row.get('payload') or {})}",
                    size=8,
                ),
            )

    parts.append(_html_heading("Context history", level=2))
    if not context_history:
        parts.append(_html_text_block("No context diffs recorded."))
    else:
        for row in context_history:
            parts.append(
                _html_text_block(
                    f"• {_iso(row.get('created_at'))} — {row.get('action', '')}\n"
                    f"{_json_block(row.get('context_diff') or {})}",
                    size=8,
                ),
            )

    parts.append(_html_heading("Session timeline", level=2))
    if not event_rows:
        parts.append(_html_text_block("No timeline events."))
    else:
        for event in event_rows:
            parts.append(
                _html_text_block(
                    f"• {_iso(event.get('occurred_at'))} — {event.get('event_type', '')}\n"
                    f"{event.get('message', '')}",
                    size=9,
                ),
            )

    parts.append(
        '<p align="center"><font face="DejaVu" size="8" color="#888888">'
        "Queenswarm · queenswarm.love · operator session report"
        "</font></p>",
    )
    return "\n".join(parts)


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

    goal = _session_goal(session)
    lines = [
        "# Queenswarm Operator Session Report",
        "",
        f"- Generated: `{generated_at.isoformat()}`",
        f"- Session: `{session_id}`",
        f"- Goal: {goal}",
        f"- Status: `{session.get('status', '')}`",
        f"- Runtime: `{session.get('runtime_mode', '')}`",
        "",
    ]
    error_text = str(session.get("error_text") or "").strip()
    if error_text:
        lines.extend([f"- Error: {error_text}", ""])
    lines.extend(["## Sub-agents", ""])
    for sub in session.get("sub_agents") or []:
        if not isinstance(sub, dict):
            continue
        lines.append(
            f"- `{sub.get('role', '?')}` · `{sub.get('status', '?')}` · `{sub.get('runtime_mode', '?')}`",
        )
    lines.extend(["", "## Deliverables (sub-agent outputs)", ""])
    output_rows = _sub_agent_output_rows(session)
    if not output_rows:
        lines.append("_No sub-agent outputs recorded yet._")
    else:
        for role, status, output in output_rows:
            lines.extend([f"### {role} · `{status}`", "", output, ""])
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

    goal = html.escape(_session_goal(session))
    status = html.escape(str(session.get("status") or ""))
    runtime = html.escape(str(session.get("runtime_mode") or ""))
    error_text = html.escape(str(session.get("error_text") or "").strip())
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
    output_blocks = "".join(
        "<section>"
        f"<h3>{html.escape(role)} · <code>{html.escape(status)}</code></h3>"
        f"<pre>{html.escape(output)}</pre>"
        "</section>"
        for role, status, output in _sub_agent_output_rows(session)
    ) or "<p><em>No sub-agent outputs recorded yet.</em></p>"

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
  {"<p><strong>Error:</strong> " + error_text + "</p>" if error_text else ""}

  <h2>Sub-agents</h2>
  <table>
    <thead><tr><th>Role</th><th>Status</th><th>Runtime</th></tr></thead>
    <tbody>{''.join(sub_rows) or '<tr><td colspan="3"><em>None</em></td></tr>'}</tbody>
  </table>

  <h2>Deliverables (sub-agent outputs)</h2>
  {output_blocks}

  <h2>Operator audit</h2>
  <ul>{audit_items}</ul>

  <h2>Context history</h2>
  <ul>{history_items}</ul>

  <h2>Session timeline</h2>
  <ul>{event_items}</ul>
</body>
</html>
"""


def _dejavu_font_paths() -> tuple[Path, Path] | None:
    """Resolve DejaVu Sans paths when bundled in the container/host."""

    regular_candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
    )
    bold_candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    )
    regular = next((path for path in regular_candidates if path.is_file()), None)
    bold = next((path for path in bold_candidates if path.is_file()), None)
    if regular is None or bold is None:
        return None
    return regular, bold


def _html_to_pdf_bytes(html_body: str) -> bytes:
    """Convert print HTML to PDF via fpdf write_html (Chrome-safe DejaVu UTF-8)."""

    from fpdf import FPDF

    dejavu = _dejavu_font_paths()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(left=14, top=16, right=14)
    if dejavu is not None:
        regular, bold = dejavu
        pdf.add_font("DejaVu", "", str(regular))
        pdf.add_font("DejaVu", "B", str(bold))
        pdf.set_font("DejaVu", size=10)
    else:
        pdf.set_font("Helvetica", size=10)
    pdf.add_page()
    pdf.write_html(html_body)
    return bytes(pdf.output())


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

    html_body = build_supervisor_session_report_print_html(
        session_id=session_id,
        session=session,
        audit_rows=audit_rows,
        event_rows=event_rows,
        context_history=context_history,
        generated_at=generated_at,
    )
    return _html_to_pdf_bytes(html_body)


__all__ = [
    "build_supervisor_session_report_html",
    "build_supervisor_session_report_markdown",
    "build_supervisor_session_report_print_html",
    "build_supervisor_session_report_pdf",
]
