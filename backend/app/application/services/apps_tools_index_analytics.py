"""Apps & Tools index analytics (read-only UX funnel telemetry)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.persistence.models.tenant import Tenant

AppsToolsFunnelEvent = Literal[
    "module_card_open",
    "module_details_open",
    "module_section_quick_link",
    "module_dependency_jump",
    "module_availability_hint_open",
    "module_beta_hint_open",
    "mcp_ops_snapshot_retry",
    "mcp_ops_retry_anomaly_ack",
    "mcp_ops_retry_anomaly_resurfaced",
    "mcp_ops_retry_anomaly_ack_reset",
    "mcp_ops_lifecycle_recommendation_open",
    "mcp_ops_lifecycle_recommendation_cooldown_block",
    "mcp_ops_lifecycle_recommendation_cooldown_override",
]

FUNNEL_AGGREGATION_EVENTS: set[str] = {
    "module_card_open",
    "module_details_open",
    "module_section_quick_link",
    "module_dependency_jump",
}

APPS_TOOLS_ANALYTICS_EVENTS: set[str] = {
    *FUNNEL_AGGREGATION_EVENTS,
    "module_availability_hint_open",
    "module_beta_hint_open",
    "mcp_ops_snapshot_retry",
    "mcp_ops_retry_anomaly_ack",
    "mcp_ops_retry_anomaly_resurfaced",
    "mcp_ops_retry_anomaly_ack_reset",
    "mcp_ops_lifecycle_recommendation_open",
    "mcp_ops_lifecycle_recommendation_cooldown_block",
    "mcp_ops_lifecycle_recommendation_cooldown_override",
}


class AppsToolsAnalyticsEventIn(BaseModel):
    """Inbound Apps & Tools analytics event payload."""

    model_config = ConfigDict(extra="ignore")

    event: AppsToolsFunnelEvent
    module_key: str = Field(min_length=2, max_length=64)
    target_module_key: str | None = Field(default=None, max_length=64)
    href: str | None = Field(default=None, max_length=512)
    source: str | None = Field(default=None, max_length=64)


class AppsToolsAnalyticsEventOut(BaseModel):
    """Normalized Apps & Tools analytics event row."""

    model_config = ConfigDict(extra="ignore")

    at: str | None = None
    event: AppsToolsFunnelEvent
    module_key: str
    target_module_key: str | None = None
    href: str | None = None
    source: str | None = None


class AppsToolsModuleFunnelOut(BaseModel):
    """Per-module funnel counters for quick solo UX optimization."""

    model_config = ConfigDict(extra="ignore")

    module_key: str
    card_open: int = 0
    details_open: int = 0
    section_quick_link: int = 0
    dependency_jump: int = 0


class AppsToolsModuleTrendOut(BaseModel):
    """Delta score between current and previous equal-size window."""

    model_config = ConfigDict(extra="ignore")

    module_key: str
    module_label: str | None = None
    current_score: int = 0
    previous_score: int = 0
    delta_score: int = 0


class AppsToolsRecommendationOut(BaseModel):
    """Read-only recommendation derived from module funnel behavior."""

    model_config = ConfigDict(extra="ignore")

    module_key: str
    module_label: str | None = None
    action: Literal["review_details", "open_sections", "check_dependencies"]
    reason: str


class AppsToolsAnalyticsSnapshotOut(BaseModel):
    """Read model for Apps & Tools analytics usage funnel."""

    model_config = ConfigDict(extra="ignore")

    window: Literal["24h", "7d", "all"] = "all"
    compact_mode: bool = False
    last_event_at: str | None = None
    total_events: int = 0
    counters: dict[str, int] = Field(default_factory=dict)
    module_funnel: list[AppsToolsModuleFunnelOut] = Field(default_factory=list)
    top_movers: list[AppsToolsModuleTrendOut] = Field(default_factory=list)
    recommendation: AppsToolsRecommendationOut | None = None
    recent_events: list[AppsToolsAnalyticsEventOut] = Field(default_factory=list)


class AppsToolsAnalyticsPreferences(TypedDict):
    """Persisted operator preference tuple for analytics widget."""

    window: Literal["24h", "7d", "all"]
    compact_mode: bool


def record_apps_tools_index_event(
    tenant: Tenant | None,
    *,
    dashboard_user_id: str,
    payload: AppsToolsAnalyticsEventIn,
) -> dict[str, int]:
    """Append one Apps & Tools index event into tenant operator settings."""

    if tenant is None:
        return {"stored_events": 0}
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("apps_tools_index_analytics") or {})
        if isinstance(root.get("apps_tools_index_analytics"), dict)
        else {}
    )
    events = list(bucket.get("events") or []) if isinstance(bucket.get("events"), list) else []
    now_iso = datetime.now(tz=UTC).isoformat()
    events.append(
        {
            "at": now_iso,
            "event": payload.event,
            "module_key": payload.module_key,
            "target_module_key": payload.target_module_key,
            "href": payload.href,
            "source": payload.source,
            "dashboard_user_id": dashboard_user_id,
        }
    )
    capped_events = events[-300:]
    counters = dict(bucket.get("counters") or {}) if isinstance(bucket.get("counters"), dict) else {}
    event_key = f"{payload.event}:{payload.module_key}"
    counters[event_key] = int(counters.get(event_key) or 0) + 1
    bucket["events"] = capped_events
    bucket["counters"] = counters
    bucket["last_event_at"] = now_iso
    root["apps_tools_index_analytics"] = bucket
    tenant.operator_settings = root
    return {"stored_events": len(capped_events)}


def compose_apps_tools_index_analytics_snapshot(
    tenant: Tenant | None,
    *,
    limit: int = 24,
    window: Literal["24h", "7d", "all"] | None = None,
) -> AppsToolsAnalyticsSnapshotOut:
    """Compose analytics snapshot from tenant operator settings bucket."""

    if tenant is None:
        return AppsToolsAnalyticsSnapshotOut()
    preferences = read_apps_tools_index_analytics_preferences(tenant)
    resolved_window: Literal["24h", "7d", "all"] = window if window is not None else preferences["window"]
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("apps_tools_index_analytics") or {})
        if isinstance(root.get("apps_tools_index_analytics"), dict)
        else {}
    )
    raw_events = list(bucket.get("events") or []) if isinstance(bucket.get("events"), list) else []
    counters_raw = dict(bucket.get("counters") or {}) if isinstance(bucket.get("counters"), dict) else {}
    events_for_window = _filter_events_by_window(raw_events, window=resolved_window)

    counters: dict[str, int] = {}
    if resolved_window == "all":
        for key, value in counters_raw.items():
            if not isinstance(key, str):
                continue
            try:
                counters[key] = max(0, int(value))
            except (TypeError, ValueError):
                continue
    else:
        for raw in events_for_window:
            parsed = _parse_event_row(raw)
            if parsed is None:
                continue
            counter_key = f"{parsed.event}:{parsed.module_key}"
            counters[counter_key] = int(counters.get(counter_key) or 0) + 1

    module_funnel_by_key: dict[str, AppsToolsModuleFunnelOut] = {}
    for key, value in counters.items():
        event_name, module_key = _parse_counter_key(key)
        if event_name is None or module_key is None:
            continue
        if event_name not in FUNNEL_AGGREGATION_EVENTS:
            continue
        row = module_funnel_by_key.setdefault(module_key, AppsToolsModuleFunnelOut(module_key=module_key))
        if event_name == "module_card_open":
            row.card_open += value
        elif event_name == "module_details_open":
            row.details_open += value
        elif event_name == "module_section_quick_link":
            row.section_quick_link += value
        elif event_name == "module_dependency_jump":
            row.dependency_jump += value

    recent_events: list[AppsToolsAnalyticsEventOut] = []
    max_rows = max(1, min(int(limit), 80))
    for raw in reversed(events_for_window[-max_rows:]):
        parsed = _parse_event_row(raw)
        if parsed is None:
            continue
        recent_events.append(parsed)

    module_funnel = sorted(
        module_funnel_by_key.values(),
        key=lambda row: _funnel_score(row),
        reverse=True,
    )
    top_movers = _compute_top_movers(raw_events, window=resolved_window, current_funnel=module_funnel)
    recommendation = _derive_recommendation(module_funnel)

    return AppsToolsAnalyticsSnapshotOut(
        window=resolved_window,
        compact_mode=preferences["compact_mode"],
        last_event_at=str(bucket.get("last_event_at") or "").strip() or None,
        total_events=len(events_for_window),
        counters=counters,
        module_funnel=module_funnel,
        top_movers=top_movers,
        recommendation=recommendation,
        recent_events=recent_events,
    )


def _parse_counter_key(key: str) -> tuple[AppsToolsFunnelEvent | None, str | None]:
    """Split ``<event>:<module_key>`` counter key into typed parts."""

    raw = key.strip()
    if ":" not in raw:
        return None, None
    event_name, module_key = raw.split(":", 1)
    module_key = module_key.strip()
    if event_name not in APPS_TOOLS_ANALYTICS_EVENTS:
        return None, None
    if not module_key:
        return None, None
    return event_name, module_key


def _parse_event_row(raw: Any) -> AppsToolsAnalyticsEventOut | None:
    """Normalize one raw tenant event row into typed event payload."""

    if not isinstance(raw, dict):
        return None
    event = str(raw.get("event") or "").strip()
    if event not in APPS_TOOLS_ANALYTICS_EVENTS:
        return None
    module_key = str(raw.get("module_key") or "").strip()
    if not module_key:
        return None
    return AppsToolsAnalyticsEventOut(
        at=str(raw.get("at") or "").strip() or None,
        event=event,
        module_key=module_key,
        target_module_key=str(raw.get("target_module_key") or "").strip() or None,
        href=str(raw.get("href") or "").strip() or None,
        source=str(raw.get("source") or "").strip() or None,
    )


def _filter_events_by_window(
    events: list[Any],
    *,
    window: Literal["24h", "7d", "all"],
) -> list[Any]:
    """Filter raw event rows to requested rolling time window."""

    if window == "all":
        return events
    hours = 24 if window == "24h" else 168
    since = datetime.now(tz=UTC) - timedelta(hours=hours)
    filtered: list[Any] = []
    for raw in events:
        if not isinstance(raw, dict):
            continue
        at = _parse_iso_datetime(str(raw.get("at") or "").strip())
        if at is None:
            continue
        if at >= since:
            filtered.append(raw)
    return filtered


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse ISO datetime and normalize to UTC for window comparisons."""

    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _funnel_score(row: AppsToolsModuleFunnelOut) -> int:
    """Compute simple module activity score for sorting and trends."""

    return row.card_open + row.details_open + row.section_quick_link + row.dependency_jump


def _compute_top_movers(
    raw_events: list[Any],
    *,
    window: Literal["24h", "7d", "all"],
    current_funnel: list[AppsToolsModuleFunnelOut],
) -> list[AppsToolsModuleTrendOut]:
    """Calculate module score deltas against previous equal-size window."""

    if window == "all":
        return []
    now = datetime.now(tz=UTC)
    current_hours = 24 if window == "24h" else 168
    current_since = now - timedelta(hours=current_hours)
    previous_since = current_since - timedelta(hours=current_hours)
    previous_until = current_since

    previous_events: list[Any] = []
    for raw in raw_events:
        if not isinstance(raw, dict):
            continue
        at = _parse_iso_datetime(str(raw.get("at") or "").strip())
        if at is None:
            continue
        if previous_since <= at < previous_until:
            previous_events.append(raw)
    previous_funnel = _funnel_from_events(previous_events)

    current_scores = {row.module_key: _funnel_score(row) for row in current_funnel}
    previous_scores = {row.module_key: _funnel_score(row) for row in previous_funnel}
    module_keys = set(current_scores) | set(previous_scores)
    trends: list[AppsToolsModuleTrendOut] = []
    for module_key in module_keys:
        current_score = int(current_scores.get(module_key) or 0)
        previous_score = int(previous_scores.get(module_key) or 0)
        delta = current_score - previous_score
        trends.append(
            AppsToolsModuleTrendOut(
                module_key=module_key,
                module_label=_module_label(module_key),
                current_score=current_score,
                previous_score=previous_score,
                delta_score=delta,
            )
        )
    trends.sort(key=lambda row: row.delta_score, reverse=True)
    return trends[:3]


def _funnel_from_events(events: list[Any]) -> list[AppsToolsModuleFunnelOut]:
    """Aggregate funnel counters directly from event rows."""

    counters: dict[str, int] = {}
    for raw in events:
        parsed = _parse_event_row(raw)
        if parsed is None:
            continue
        key = f"{parsed.event}:{parsed.module_key}"
        counters[key] = int(counters.get(key) or 0) + 1
    by_module: dict[str, AppsToolsModuleFunnelOut] = {}
    for key, value in counters.items():
        event_name, module_key = _parse_counter_key(key)
        if event_name is None or module_key is None:
            continue
        row = by_module.setdefault(module_key, AppsToolsModuleFunnelOut(module_key=module_key))
        if event_name == "module_card_open":
            row.card_open += value
        elif event_name == "module_details_open":
            row.details_open += value
        elif event_name == "module_section_quick_link":
            row.section_quick_link += value
        elif event_name == "module_dependency_jump":
            row.dependency_jump += value
    return sorted(by_module.values(), key=_funnel_score, reverse=True)


def _derive_recommendation(
    module_funnel: list[AppsToolsModuleFunnelOut],
) -> AppsToolsRecommendationOut | None:
    """Derive one read-only operator hint from the strongest module signal."""

    if not module_funnel:
        return None
    top = module_funnel[0]
    card = max(0, int(top.card_open))
    details = max(0, int(top.details_open))
    sections = max(0, int(top.section_quick_link))
    if card > 0 and details * 2 < card:
        return AppsToolsRecommendationOut(
            module_key=top.module_key,
            module_label=_module_label(top.module_key),
            action="review_details",
            reason="High card opens but low details opens; validate governance and capability fit.",
        )
    if details > 0 and sections == 0:
        return AppsToolsRecommendationOut(
            module_key=top.module_key,
            module_label=_module_label(top.module_key),
            action="open_sections",
            reason="Details are viewed, but section deep-links are unused; continue into module workflow sections.",
        )
    return AppsToolsRecommendationOut(
        module_key=top.module_key,
        module_label=_module_label(top.module_key),
        action="check_dependencies",
        reason="Module engagement is healthy; review dependency jumps for cross-module optimization.",
    )


def _module_label(module_key: str) -> str:
    """Human label fallback for analytics rows."""

    pretty = module_key.replace("_", " ").strip()
    return " ".join(part.capitalize() for part in pretty.split())


def read_apps_tools_index_analytics_preferences(
    tenant: Tenant | None,
) -> AppsToolsAnalyticsPreferences:
    """Return persisted Apps & Tools analytics preferences with safe defaults."""

    defaults: AppsToolsAnalyticsPreferences = {"window": "24h", "compact_mode": False}
    if tenant is None:
        return defaults
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("apps_tools_index_analytics") or {})
        if isinstance(root.get("apps_tools_index_analytics"), dict)
        else {}
    )
    pref = dict(bucket.get("preferences") or {}) if isinstance(bucket.get("preferences"), dict) else {}
    window_raw = str(pref.get("window") or "").strip()
    window: Literal["24h", "7d", "all"] = "24h"
    if window_raw in {"24h", "7d", "all"}:
        window = window_raw
    compact_mode = bool(pref.get("compact_mode"))
    return {"window": window, "compact_mode": compact_mode}


def persist_apps_tools_index_analytics_preferences(
    tenant: Tenant | None,
    *,
    window: Literal["24h", "7d", "all"] | None = None,
    compact_mode: bool | None = None,
) -> AppsToolsAnalyticsPreferences:
    """Persist Apps & Tools analytics preferences into tenant operator settings."""

    current = read_apps_tools_index_analytics_preferences(tenant)
    next_window = window if window is not None else current["window"]
    next_compact_mode = compact_mode if compact_mode is not None else current["compact_mode"]
    result = {"window": next_window, "compact_mode": bool(next_compact_mode)}
    if tenant is None:
        return result
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("apps_tools_index_analytics") or {})
        if isinstance(root.get("apps_tools_index_analytics"), dict)
        else {}
    )
    bucket["preferences"] = result
    root["apps_tools_index_analytics"] = bucket
    tenant.operator_settings = root
    return result


__all__ = [
    "AppsToolsAnalyticsEventIn",
    "AppsToolsRecommendationOut",
    "AppsToolsAnalyticsSnapshotOut",
    "compose_apps_tools_index_analytics_snapshot",
    "persist_apps_tools_index_analytics_preferences",
    "read_apps_tools_index_analytics_preferences",
    "record_apps_tools_index_event",
]
