"""Read latest HA chaos smoke evidence from on-disk reports (host-mounted in prod)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_STAMP_RE = re.compile(r"ha-chaos-(\d{8}T\d{6}Z)\.json$")


def resolve_ha_reports_dir() -> Path | None:
    """Return configured HA reports directory when it exists."""

    raw = (settings.ha_reports_dir or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.is_dir():
        return None
    return path


def _parse_stamp_from_name(name: str) -> datetime | None:
    """Parse UTC timestamp embedded in ha-chaos report filename."""

    match = _STAMP_RE.search(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def _load_json_report(path: Path) -> dict[str, Any] | None:
    """Load structured HA chaos sidecar JSON."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.info("ha_chaos_evidence.json_read_failed", path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def load_latest_ha_chaos_evidence() -> dict[str, Any]:
    """Return latest HA chaos drill evidence or empty defaults."""

    empty: dict[str, Any] = {
        "report_available": False,
        "last_drill_at": None,
        "passed": None,
        "baseline_ready_code": None,
        "degraded_ready_code": None,
        "recovered_ready_code": None,
        "expect_failover_ready": False,
        "report_file": None,
        "reports_dir": None,
    }

    reports_dir = resolve_ha_reports_dir()
    if reports_dir is None:
        return empty

    empty["reports_dir"] = str(reports_dir)

    json_reports = sorted(reports_dir.glob("ha-chaos-*.json"), reverse=True)
    if not json_reports:
        return empty

    payload = _load_json_report(json_reports[0])
    if not payload:
        return empty

    return {
        "report_available": True,
        "last_drill_at": payload.get("timestamp_utc"),
        "passed": payload.get("passed"),
        "baseline_ready_code": payload.get("baseline_ready_code"),
        "degraded_ready_code": payload.get("degraded_ready_code"),
        "recovered_ready_code": payload.get("recovered_ready_code"),
        "expect_failover_ready": payload.get("expect_failover_ready") is True,
        "report_file": payload.get("report_file") or json_reports[0].name,
        "reports_dir": str(reports_dir),
    }


__all__ = ["load_latest_ha_chaos_evidence", "resolve_ha_reports_dir"]
