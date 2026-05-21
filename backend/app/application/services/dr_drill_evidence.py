"""Read latest DR drill evidence from on-disk reports (host-mounted in prod)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_STAMP_RE = re.compile(r"dr-drill-(\d{8}T\d{6}Z)\.(md|json)$")


def resolve_dr_reports_dir() -> Path | None:
    """Return configured DR reports directory when it exists."""

    raw = (settings.dr_reports_dir or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_dir():
        return None
    return path


def _parse_stamp_from_name(name: str) -> datetime | None:
    """Parse UTC timestamp embedded in dr-drill report filename."""

    match = _STAMP_RE.search(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def _load_json_report(path: Path) -> dict[str, Any] | None:
    """Load structured DR drill sidecar JSON."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.info("dr_drill_evidence.json_read_failed", path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _load_md_report(path: Path) -> dict[str, Any] | None:
    """Parse minimal fields from markdown DR drill report."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.info("dr_drill_evidence.md_read_failed", path=str(path), error=str(exc))
        return None

    backup_sec: int | None = None
    restore_status = "unknown"
    for line in text.splitlines():
        if line.startswith("- Backup duration (sec):"):
            try:
                backup_sec = int(line.split(":", 1)[1].strip())
            except ValueError:
                backup_sec = None
        if line.startswith("- Restore status:"):
            restore_status = line.split(":", 1)[1].strip()

    stamp = _parse_stamp_from_name(path.name)
    return {
        "timestamp_utc": stamp.isoformat() if stamp else None,
        "backup_duration_sec": backup_sec,
        "restore_status": restore_status,
        "report_file": path.name,
    }


def load_latest_dr_drill_evidence() -> dict[str, Any]:
    """Return latest DR drill evidence or empty defaults."""

    empty: dict[str, Any] = {
        "report_available": False,
        "last_drill_at": None,
        "backup_duration_sec": None,
        "restore_status": None,
        "report_file": None,
        "reports_dir": None,
    }

    reports_dir = resolve_dr_reports_dir()
    if reports_dir is None:
        return empty

    empty["reports_dir"] = str(reports_dir)

    json_reports = sorted(reports_dir.glob("dr-drill-*.json"), reverse=True)
    if json_reports:
        payload = _load_json_report(json_reports[0])
        if payload:
            return {
                "report_available": True,
                "last_drill_at": payload.get("timestamp_utc"),
                "backup_duration_sec": payload.get("backup_duration_sec"),
                "restore_status": payload.get("restore_status"),
                "report_file": payload.get("report_file") or json_reports[0].name,
                "reports_dir": str(reports_dir),
            }

    md_reports = sorted(reports_dir.glob("dr-drill-*.md"), reverse=True)
    if md_reports:
        payload = _load_md_report(md_reports[0])
        if payload and (payload.get("timestamp_utc") or payload.get("backup_duration_sec") is not None):
            return {
                "report_available": True,
                "last_drill_at": payload.get("timestamp_utc"),
                "backup_duration_sec": payload.get("backup_duration_sec"),
                "restore_status": payload.get("restore_status"),
                "report_file": payload.get("report_file"),
                "reports_dir": str(reports_dir),
            }

    return empty


__all__ = ["load_latest_dr_drill_evidence", "resolve_dr_reports_dir"]
