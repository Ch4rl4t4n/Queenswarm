"""Aggregate Execution Studio activity feed into operator telemetry."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from app.infrastructure.persistence.models.tenant import Tenant

from app.application.services.execution_studio_activity import list_execution_activity

_CONNECTOR_MSG = re.compile(r"(?:Executed|Simulated|Draft preview|Auto-simulate external proposal):\s*([^/\s]+)/")


def build_activity_telemetry(tenant: Tenant | None, *, limit: int = 40) -> dict[str, Any]:
    """Summarize recent activity for cost/connector/browser observability."""

    rows = list_execution_activity(tenant, limit=limit)
    by_type: Counter[str] = Counter()
    by_connector: Counter[str] = Counter()
    connector_cost_blocks: Counter[str] = Counter()
    cost_blocks = 0
    browser_steps = 0
    proposals = 0
    maintainer_runs = 0
    tool_executes = 0

    for row in rows:
        event_type = str(row.get("event_type") or "unknown")
        by_type[event_type] += 1
        message = str(row.get("message") or "").lower()
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        connector_slug = str(payload.get("connector_slug") or "").strip().lower()
        if not connector_slug:
            matched = _CONNECTOR_MSG.search(str(row.get("message") or ""))
            if matched:
                connector_slug = matched.group(1).strip().lower()

        if event_type == "tool_execute":
            tool_executes += 1
            if connector_slug:
                by_connector[connector_slug] += 1
        if event_type == "browser_step":
            browser_steps += 1
        if event_type == "proposal_created":
            proposals += 1
        if event_type == "maintainer_run":
            maintainer_runs += 1
        if "cost_tier_blocked" in message or payload.get("error") == "cost_tier_blocked":
            cost_blocks += 1
            if connector_slug:
                connector_cost_blocks[connector_slug] += 1

    all_slugs = sorted(set(by_connector.keys()) | set(connector_cost_blocks.keys()))
    connector_chart = [
        {
            "slug": slug,
            "runs": by_connector.get(slug, 0),
            "blocks": connector_cost_blocks.get(slug, 0),
        }
        for slug in all_slugs
    ]

    hour_buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"runs": 0, "blocks": 0})
    for row in rows:
        at_raw = str(row.get("at") or "")
        bucket = at_raw[:13] if len(at_raw) >= 13 else "unknown"
        event_type = str(row.get("event_type") or "")
        message = str(row.get("message") or "").lower()
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if event_type == "tool_execute":
            hour_buckets[bucket]["runs"] += 1
        if "cost_tier_blocked" in message or payload.get("error") == "cost_tier_blocked":
            hour_buckets[bucket]["blocks"] += 1

    activity_time_series = [
        {"bucket": bucket, "runs": values["runs"], "blocks": values["blocks"]}
        for bucket, values in sorted(hour_buckets.items())
        if bucket != "unknown"
    ][-24:]

    return {
        "total_events": len(rows),
        "by_event_type": dict(by_type),
        "by_connector": dict(by_connector),
        "connector_cost_blocks": dict(connector_cost_blocks),
        "connector_chart": connector_chart,
        "activity_time_series": activity_time_series,
        "tool_executes": tool_executes,
        "browser_steps": browser_steps,
        "proposals_created": proposals,
        "maintainer_runs": maintainer_runs,
        "cost_tier_blocks": cost_blocks,
        "window_limit": limit,
    }


__all__ = ["build_activity_telemetry"]
