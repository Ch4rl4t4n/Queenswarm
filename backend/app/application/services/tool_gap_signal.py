"""Record actionable MCP tool gaps from failed invocations (Redis, tenant-scoped)."""

from __future__ import annotations

import re
import time
import uuid
from typing import Any, Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_json, set_json
from app.infrastructure.connectors.phase3.catalog import iter_phase3_templates

logger = get_logger(__name__)

ToolGapKind = Literal[
    "connector_missing",
    "tool_missing",
    "manager_allowlist",
    "permission_missing",
]

_GAP_TTL_SEC = 604_800  # 7 days
_MAX_GAPS = 30

_SLUG_IN_MSG = re.compile(r"`([^`]+)`")


def _extract_backtick_token(message: str) -> str | None:
    match = _SLUG_IN_MSG.search(message)
    if match is None:
        return None
    token = match.group(1).strip().lower()
    return token or None


def classify_tool_gap(
    *,
    result: str,
    connector_slug: str,
    tool_name: str,
    manager_slug: str,
) -> dict[str, Any] | None:
    """Return gap metadata when an MCP failure is operator-actionable."""

    raw = str(result or "").strip()
    slug = connector_slug.strip().lower()
    tool = tool_name.strip().lower()
    manager = manager_slug.strip().lower()

    if raw.startswith("mcp_invoke blocked"):
        blocked = _extract_backtick_token(raw) or slug
        return {
            "kind": "manager_allowlist",
            "connector_slug": blocked,
            "tool_name": tool or "invoke",
            "manager_slug": manager or None,
            "message": raw[:240],
            "occurrences": 1,
        }

    if not raw.startswith("dynamic_invoke_error:"):
        return None

    detail = raw.removeprefix("dynamic_invoke_error:").strip()

    if "inactive or unknown" in detail:
        missing = _extract_backtick_token(detail) or slug
        return {
            "kind": "connector_missing",
            "connector_slug": missing,
            "tool_name": tool or "invoke",
            "manager_slug": manager or None,
            "message": raw[:240],
            "occurrences": 1,
        }

    if "missing from manifest" in detail:
        missing_tool = _extract_backtick_token(detail) or tool
        return {
            "kind": "tool_missing",
            "connector_slug": slug,
            "tool_name": missing_tool or tool or "invoke",
            "manager_slug": manager or None,
            "message": raw[:240],
            "occurrences": 1,
        }

    if "not allowlisted for manager" in detail:
        return {
            "kind": "manager_allowlist",
            "connector_slug": slug,
            "tool_name": tool or "invoke",
            "manager_slug": _extract_backtick_token(detail) or manager or None,
            "message": raw[:240],
            "occurrences": 1,
        }

    if detail.startswith("missing_permission("):
        perm = detail.removeprefix("missing_permission(").removesuffix(")").strip().lower()
        return {
            "kind": "permission_missing",
            "connector_slug": slug,
            "tool_name": tool or "invoke",
            "manager_slug": manager or None,
            "permission": perm or None,
            "message": raw[:240],
            "occurrences": 1,
        }

    return None


def integrations_href_for_template(template_id: str | None = None) -> str:
    """Canonical Integrations URL for resolving a tool gap."""

    if template_id:
        return f"/integrations?tab=marketplace&template={template_id}"
    return "/integrations?tab=marketplace"


def suggest_phase3_template_id(connector_slug: str) -> str | None:
    """Best-effort Phase3 template match for a missing connector slug."""

    needle = connector_slug.strip().lower()
    if not needle:
        return None
    for template in iter_phase3_templates():
        slug = str(template.suggested_slug or "").strip().lower()
        tid = str(template.template_id or "").strip().lower()
        if needle == slug or needle in slug or slug in needle or needle.replace("_", "-") in tid:
            return template.template_id
    return None


def _gap_key(tenant_id: uuid.UUID) -> str:
    return f"qs:tool_gaps:v1:{tenant_id}"


async def record_tool_gap(
    *,
    tenant_id: uuid.UUID,
    connector_slug: str,
    tool_name: str,
    manager_slug: str,
    result: str,
) -> None:
    """Persist one actionable gap (deduped, capped) when feature flag is on."""

    if not settings.tool_gap_signal_enabled:
        return

    gap = classify_tool_gap(
        result=result,
        connector_slug=connector_slug,
        tool_name=tool_name,
        manager_slug=manager_slug,
    )
    if gap is None:
        return

    template_id = suggest_phase3_template_id(str(gap.get("connector_slug") or connector_slug))
    if template_id:
        gap["suggested_template_id"] = template_id
    gap["integrations_href"] = integrations_href_for_template(template_id)

    gap["last_seen_epoch"] = time.time()
    key = _gap_key(tenant_id)

    try:
        blob = await get_json(key) or {"gaps": []}
    except Exception:
        blob = {"gaps": []}

    gaps: list[dict[str, Any]] = [row for row in list(blob.get("gaps") or []) if isinstance(row, dict)]
    kind = str(gap.get("kind") or "")
    slug_key = str(gap.get("connector_slug") or "").strip().lower()
    tool_key = str(gap.get("tool_name") or "").strip().lower()

    merged = gap
    for existing in gaps:
        if (
            str(existing.get("kind") or "") == kind
            and str(existing.get("connector_slug") or "").strip().lower() == slug_key
            and str(existing.get("tool_name") or "").strip().lower() == tool_key
        ):
            merged = {
                **existing,
                **gap,
                "occurrences": int(existing.get("occurrences") or 0) + 1,
            }
            gaps.remove(existing)
            break

    gaps.insert(0, merged)
    gaps = gaps[:_MAX_GAPS]

    try:
        await set_json(key, {"gaps": gaps, "updated_at_epoch": time.time()}, ttl=_GAP_TTL_SEC)
    except Exception as exc:
        logger.warning(
            "tool_gap.record_failed",
            tenant_id=str(tenant_id),
            connector_slug=slug_key,
            error=str(exc),
        )
        return

    logger.info(
        "tool_gap.recorded",
        tenant_id=str(tenant_id),
        connector_slug=slug_key,
        tool_name=tool_key,
        kind=kind,
    )


async def list_tool_gaps(*, tenant_id: uuid.UUID, limit: int = 12) -> list[dict[str, Any]]:
    """Return recent actionable gaps for operator dashboards."""

    if not settings.tool_gap_signal_enabled:
        return []
    key = _gap_key(tenant_id)
    try:
        blob = await get_json(key)
    except Exception:
        return []
    if not isinstance(blob, dict):
        return []
    gaps = [row for row in list(blob.get("gaps") or []) if isinstance(row, dict)]
    return gaps[: max(1, min(int(limit), _MAX_GAPS))]


__all__ = [
    "classify_tool_gap",
    "integrations_href_for_template",
    "list_tool_gaps",
    "record_tool_gap",
    "suggest_phase3_template_id",
]
