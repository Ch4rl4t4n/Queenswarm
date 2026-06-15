"""TR1 — Injection guard telemetry store (3-checkpoint model)."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from app.application.services.prompt_injection_guard import InjectionCheckpoint
from app.core.tenant_context import get_current_tenant_uuid

TELEMETRY_BUCKET = "injection_guard_telemetry"
RECENT_HIT_LIMIT = 12

GUARDED_EXTERNAL_TOOLS: tuple[tuple[str, str], ...] = (
    ("web_search", "Web search"),
    ("scrape_url", "Scrape URL"),
    ("wikipedia", "Wikipedia"),
    ("grokipedia", "Grokipedia"),
    ("serper_search", "Serper search"),
    ("tavily_search", "Tavily search"),
    ("jina_reader", "Jina reader"),
)

CHECKPOINT_LABELS: dict[str, str] = {
    InjectionCheckpoint.OPERATOR_INPUT.value: "Operator input",
    InjectionCheckpoint.EXTERNAL_TOOL.value: "External tool",
    InjectionCheckpoint.AGENT_OUTPUT.value: "Agent output",
}


def _empty_bucket() -> dict[str, Any]:
    return {
        "checkpoints": {
            InjectionCheckpoint.OPERATOR_INPUT.value: {"scans": 0, "blocked": 0},
            InjectionCheckpoint.EXTERNAL_TOOL.value: {"scans": 0, "blocked": 0},
            InjectionCheckpoint.AGENT_OUTPUT.value: {"scans": 0, "blocked": 0},
        },
        "tools": {},
        "recent_hits": [],
        "updated_at": None,
    }


def _telemetry_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(TELEMETRY_BUCKET)
    if not isinstance(bucket, dict):
        return _empty_bucket()
    merged = _empty_bucket()
    for checkpoint, row in (bucket.get("checkpoints") or {}).items():
        if checkpoint in merged["checkpoints"] and isinstance(row, dict):
            merged["checkpoints"][checkpoint] = {
                "scans": max(0, int(row.get("scans") or 0)),
                "blocked": max(0, int(row.get("blocked") or 0)),
            }
    tools = bucket.get("tools")
    if isinstance(tools, dict):
        merged["tools"] = {
            str(key): {
                "scans": max(0, int((value or {}).get("scans") or 0)),
                "blocked": max(0, int((value or {}).get("blocked") or 0)),
            }
            for key, value in tools.items()
            if isinstance(value, dict)
        }
    recent = bucket.get("recent_hits")
    if isinstance(recent, list):
        merged["recent_hits"] = [row for row in recent if isinstance(row, dict)][:RECENT_HIT_LIMIT]
    merged["updated_at"] = bucket.get("updated_at")
    return merged


def merge_telemetry_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Merge injection guard telemetry patch into tenant operator_settings."""

    root = dict(operator_settings or {})
    bucket = _telemetry_bucket(root)
    for checkpoint, delta in (patch.get("checkpoints") or {}).items():
        if checkpoint not in bucket["checkpoints"]:
            continue
        row = bucket["checkpoints"][checkpoint]
        row["scans"] = max(0, int(row.get("scans") or 0) + int(delta.get("scans") or 0))
        row["blocked"] = max(0, int(row.get("blocked") or 0) + int(delta.get("blocked") or 0))
    for tool_name, delta in (patch.get("tools") or {}).items():
        norm = str(tool_name).strip()
        if not norm:
            continue
        row = dict(bucket["tools"].get(norm) or {"scans": 0, "blocked": 0})
        row["scans"] = max(0, int(row.get("scans") or 0) + int(delta.get("scans") or 0))
        row["blocked"] = max(0, int(row.get("blocked") or 0) + int(delta.get("blocked") or 0))
        bucket["tools"][norm] = row
    recent = list(bucket.get("recent_hits") or [])
    for hit in patch.get("recent_hits") or []:
        if isinstance(hit, dict):
            recent.insert(0, hit)
    bucket["recent_hits"] = recent[:RECENT_HIT_LIMIT]
    bucket["updated_at"] = datetime.now(tz=UTC).isoformat()
    root[TELEMETRY_BUCKET] = bucket
    return root


class InjectionGuardTelemetryStore:
    """Thread-safe in-process buffer flushed into tenant settings on dashboard read."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[str, dict[str, Any]] = {}

    def record_scan(
        self,
        *,
        tenant_id: uuid.UUID | None,
        checkpoint: InjectionCheckpoint | str,
        blocked: bool,
        tool_name: str | None = None,
        matched_pattern: str | None = None,
    ) -> None:
        """Record one guard scan (blocked or allowed)."""

        resolved = tenant_id or get_current_tenant_uuid()
        if resolved is None:
            return
        cp = str(checkpoint.value if isinstance(checkpoint, InjectionCheckpoint) else checkpoint)
        patch: dict[str, Any] = {
            "checkpoints": {cp: {"scans": 1, "blocked": 1 if blocked else 0}},
            "tools": {},
            "recent_hits": [],
        }
        tool = str(tool_name or "").strip()
        if tool:
            patch["tools"][tool] = {"scans": 1, "blocked": 1 if blocked else 0}
        if blocked:
            patch["recent_hits"].append(
                {
                    "at": datetime.now(tz=UTC).isoformat(),
                    "checkpoint": cp,
                    "tool_name": tool or None,
                    "matched_pattern": matched_pattern,
                },
            )
        key = str(resolved)
        with self._lock:
            existing = self._pending.get(key)
            if existing is None:
                self._pending[key] = patch
            else:
                self._pending[key] = _merge_patch(existing, patch)

    def drain_patch(self, tenant_id: uuid.UUID) -> dict[str, Any] | None:
        """Return and clear pending patch for one tenant."""

        key = str(tenant_id)
        with self._lock:
            patch = self._pending.pop(key, None)
        return patch


def _merge_patch(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return merge_telemetry_patch({TELEMETRY_BUCKET: left}, right)[TELEMETRY_BUCKET]


injection_guard_store = InjectionGuardTelemetryStore()


def telemetry_bucket_from_settings(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    """Public accessor for persisted telemetry bucket."""

    return _telemetry_bucket(operator_settings)


__all__ = [
    "CHECKPOINT_LABELS",
    "GUARDED_EXTERNAL_TOOLS",
    "TELEMETRY_BUCKET",
    "InjectionGuardTelemetryStore",
    "injection_guard_store",
    "merge_telemetry_patch",
    "telemetry_bucket_from_settings",
]
