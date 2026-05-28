"""Unit tests for Apps & Tools index analytics event recorder."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.application.services.apps_tools_index_analytics import (
    AppsToolsAnalyticsEventIn,
    compose_apps_tools_index_analytics_snapshot,
    persist_apps_tools_index_analytics_preferences,
    read_apps_tools_index_analytics_preferences,
    record_apps_tools_index_event,
)


def test_record_apps_tools_index_event_appends_and_counts() -> None:
    """Recorder stores bounded event feed and per-module funnel counters."""

    tenant = SimpleNamespace(operator_settings={})

    first = AppsToolsAnalyticsEventIn(
        event="module_card_open",
        module_key="marketing_automation",
        href="/apps-tools/marketing-automation",
        source="module_card",
    )
    second = AppsToolsAnalyticsEventIn(
        event="module_details_open",
        module_key="marketing_automation",
        source="module_card",
    )

    record_apps_tools_index_event(tenant, dashboard_user_id="user-1", payload=first)
    out = record_apps_tools_index_event(tenant, dashboard_user_id="user-1", payload=second)

    bucket = tenant.operator_settings["apps_tools_index_analytics"]
    assert out["stored_events"] == 2
    assert bucket["events"][-1]["event"] == "module_details_open"
    assert bucket["counters"]["module_card_open:marketing_automation"] == 1
    assert bucket["counters"]["module_details_open:marketing_automation"] == 1


def test_record_apps_tools_index_event_caps_feed_length() -> None:
    """Recorder keeps only the newest 300 events in tenant settings."""

    tenant = SimpleNamespace(operator_settings={})
    payload = AppsToolsAnalyticsEventIn(event="module_card_open", module_key="research_workspace")

    for idx in range(310):
        record_apps_tools_index_event(tenant, dashboard_user_id=f"user-{idx}", payload=payload)

    bucket = tenant.operator_settings["apps_tools_index_analytics"]
    assert len(bucket["events"]) == 300


def test_compose_apps_tools_index_analytics_snapshot_aggregates_module_funnel() -> None:
    """Snapshot composes per-module funnel counters from raw counter keys."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "last_event_at": "2026-05-27T12:00:00+00:00",
                "events": [
                    {
                        "event": "module_card_open",
                        "module_key": "marketing_automation",
                        "at": "2026-05-27T11:58:00+00:00",
                    },
                    {
                        "event": "module_details_open",
                        "module_key": "marketing_automation",
                        "at": "2026-05-27T11:59:00+00:00",
                    },
                ],
                "counters": {
                    "module_card_open:marketing_automation": 4,
                    "module_details_open:marketing_automation": 3,
                    "module_section_quick_link:research_workspace": 2,
                    "module_dependency_jump:research_workspace": 1,
                    "invalid": 9,
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=20, window="all")

    assert snapshot.window == "all"
    assert snapshot.total_events == 2
    assert snapshot.last_event_at == "2026-05-27T12:00:00+00:00"
    assert len(snapshot.recent_events) == 2
    assert snapshot.module_funnel[0].module_key == "marketing_automation"
    assert snapshot.module_funnel[0].card_open == 4
    assert snapshot.module_funnel[0].details_open == 3
    assert snapshot.module_funnel[1].module_key == "research_workspace"
    assert snapshot.module_funnel[1].section_quick_link == 2
    assert snapshot.module_funnel[1].dependency_jump == 1
    assert snapshot.recommendation is not None
    assert snapshot.recommendation.module_key == "marketing_automation"


def test_compose_apps_tools_index_analytics_snapshot_ignores_invalid_rows() -> None:
    """Snapshot filters malformed event rows and non-int counters safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "events": [{"event": "unknown_event", "module_key": "foo"}, "bad-row"],
                "counters": {
                    "module_card_open:marketing_automation": "7",
                    "module_details_open:marketing_automation": "oops",
                    123: 1,
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.total_events == 2
    assert len(snapshot.recent_events) == 0
    assert snapshot.counters["module_card_open:marketing_automation"] == 7
    assert "module_details_open:marketing_automation" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_keeps_retry_telemetry_outside_funnel() -> None:
    """Retry telemetry is preserved in counters but excluded from funnel score rows."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_snapshot_retry:mcp_ops_studio": 2,
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_snapshot_retry:mcp_ops_studio"] == 2
    assert snapshot.module_funnel == []


def test_compose_apps_tools_index_analytics_snapshot_sanitizes_malformed_retry_counters() -> None:
    """Malformed retry counter values are sanitized or ignored safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_snapshot_retry:mcp_ops_studio": -4,
                    "mcp_ops_snapshot_retry:content_factory": "NaN",
                    "mcp_ops_snapshot_retry:research_workspace": "3",
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_snapshot_retry:mcp_ops_studio"] == 0
    assert snapshot.counters["mcp_ops_snapshot_retry:research_workspace"] == 3
    assert "mcp_ops_snapshot_retry:content_factory" not in snapshot.counters
    assert snapshot.module_funnel == []


def test_compose_apps_tools_index_analytics_snapshot_sanitizes_malformed_ack_counters() -> None:
    """Malformed anomaly-ack counters are clamped/filtered safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_retry_anomaly_ack:mcp_ops_studio": -1,
                    "mcp_ops_retry_anomaly_ack:content_factory": "NaN",
                    "mcp_ops_retry_anomaly_ack:research_workspace": "2",
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_retry_anomaly_ack:mcp_ops_studio"] == 0
    assert snapshot.counters["mcp_ops_retry_anomaly_ack:research_workspace"] == 2
    assert "mcp_ops_retry_anomaly_ack:content_factory" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_sanitizes_malformed_ack_reset_counters() -> None:
    """Malformed anomaly-ack-reset counters are clamped/filtered safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_retry_anomaly_ack_reset:mcp_ops_studio": -9,
                    "mcp_ops_retry_anomaly_ack_reset:content_factory": "NaN",
                    "mcp_ops_retry_anomaly_ack_reset:research_workspace": "3",
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_retry_anomaly_ack_reset:mcp_ops_studio"] == 0
    assert snapshot.counters["mcp_ops_retry_anomaly_ack_reset:research_workspace"] == 3
    assert "mcp_ops_retry_anomaly_ack_reset:content_factory" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_sanitizes_malformed_lifecycle_recommendation_counters() -> None:
    """Malformed lifecycle recommendation counters are clamped/filtered safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_lifecycle_recommendation_open:mcp_ops_studio": -2,
                    "mcp_ops_lifecycle_recommendation_open:content_factory": "NaN",
                    "mcp_ops_lifecycle_recommendation_open:research_workspace": "4",
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_lifecycle_recommendation_open:mcp_ops_studio"] == 0
    assert snapshot.counters["mcp_ops_lifecycle_recommendation_open:research_workspace"] == 4
    assert "mcp_ops_lifecycle_recommendation_open:content_factory" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_sanitizes_malformed_lifecycle_cooldown_block_counters() -> None:
    """Malformed lifecycle cooldown-block counters are clamped/filtered safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_lifecycle_recommendation_cooldown_block:mcp_ops_studio": -1,
                    "mcp_ops_lifecycle_recommendation_cooldown_block:content_factory": "NaN",
                    "mcp_ops_lifecycle_recommendation_cooldown_block:research_workspace": "5",
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_lifecycle_recommendation_cooldown_block:mcp_ops_studio"] == 0
    assert snapshot.counters["mcp_ops_lifecycle_recommendation_cooldown_block:research_workspace"] == 5
    assert "mcp_ops_lifecycle_recommendation_cooldown_block:content_factory" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_sanitizes_malformed_lifecycle_cooldown_override_counters() -> None:
    """Malformed lifecycle cooldown-override counters are clamped/filtered safely."""

    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "counters": {
                    "mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio": -3,
                    "mcp_ops_lifecycle_recommendation_cooldown_override:content_factory": "NaN",
                    "mcp_ops_lifecycle_recommendation_cooldown_override:research_workspace": "6",
                },
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=8, window="all")

    assert snapshot.counters["mcp_ops_lifecycle_recommendation_cooldown_override:mcp_ops_studio"] == 0
    assert snapshot.counters["mcp_ops_lifecycle_recommendation_cooldown_override:research_workspace"] == 6
    assert "mcp_ops_lifecycle_recommendation_cooldown_override:content_factory" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_handles_mixed_retry_and_ack_event_ordering() -> None:
    """Windowed event aggregation handles mixed retry/ack ordering deterministically."""

    now = datetime.now(tz=UTC)
    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "events": [
                    {
                        "event": "mcp_ops_snapshot_retry",
                        "module_key": "mcp_ops_studio",
                        "at": (now - timedelta(minutes=5)).isoformat(),
                    },
                    {
                        "event": "mcp_ops_retry_anomaly_ack",
                        "module_key": "mcp_ops_studio",
                        "at": (now - timedelta(minutes=2)).isoformat(),
                    },
                    {
                        "event": "mcp_ops_snapshot_retry",
                        "module_key": "mcp_ops_studio",
                        "at": (now - timedelta(minutes=1)).isoformat(),
                    },
                ],
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, window="24h", limit=10)

    assert snapshot.counters["mcp_ops_snapshot_retry:mcp_ops_studio"] == 2
    assert snapshot.counters["mcp_ops_retry_anomaly_ack:mcp_ops_studio"] == 1
    assert snapshot.recent_events[0].event == "mcp_ops_snapshot_retry"
    assert snapshot.recent_events[1].event == "mcp_ops_retry_anomaly_ack"


def test_compose_apps_tools_index_analytics_snapshot_filters_window() -> None:
    """Windowed snapshot returns only events inside rolling horizon."""

    recent = (datetime.now(tz=UTC) - timedelta(hours=4)).isoformat()
    old = (datetime.now(tz=UTC) - timedelta(hours=40)).isoformat()
    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "events": [
                    {"event": "module_card_open", "module_key": "marketing_automation", "at": old},
                    {"event": "module_details_open", "module_key": "marketing_automation", "at": recent},
                ],
                "counters": {"module_card_open:marketing_automation": 10},
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, window="24h", limit=10)

    assert snapshot.window == "24h"
    assert snapshot.total_events == 1
    assert snapshot.counters["module_details_open:marketing_automation"] == 1
    assert "module_card_open:marketing_automation" not in snapshot.counters


def test_compose_apps_tools_index_analytics_snapshot_computes_top_movers() -> None:
    """Windowed snapshot includes score deltas versus previous window."""

    now = datetime.now(tz=UTC)
    recent = (now - timedelta(hours=2)).isoformat()
    prev = (now - timedelta(hours=26)).isoformat()
    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "events": [
                    {"event": "module_card_open", "module_key": "marketing_automation", "at": prev},
                    {"event": "module_card_open", "module_key": "marketing_automation", "at": recent},
                    {"event": "module_details_open", "module_key": "marketing_automation", "at": recent},
                ],
            }
        }
    )

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, window="24h", limit=10)

    assert snapshot.top_movers
    mover = snapshot.top_movers[0]
    assert mover.module_key == "marketing_automation"
    assert mover.module_label == "Marketing Automation"
    assert mover.current_score == 2
    assert mover.previous_score == 1
    assert mover.delta_score == 1


def test_persist_apps_tools_index_analytics_preferences_updates_tenant_settings() -> None:
    """Preference patch persists selected window and compact mode."""

    tenant = SimpleNamespace(operator_settings={})
    out = persist_apps_tools_index_analytics_preferences(tenant, window="7d", compact_mode=True)

    assert out["window"] == "7d"
    assert out["compact_mode"] is True
    read_back = read_apps_tools_index_analytics_preferences(tenant)
    assert read_back["window"] == "7d"
    assert read_back["compact_mode"] is True


def test_snapshot_uses_persisted_window_when_window_not_passed() -> None:
    """Snapshot applies persisted preference when caller omits explicit window."""

    now = datetime.now(tz=UTC)
    recent = (now - timedelta(hours=2)).isoformat()
    old = (now - timedelta(hours=30)).isoformat()
    tenant = SimpleNamespace(
        operator_settings={
            "apps_tools_index_analytics": {
                "events": [
                    {"event": "module_card_open", "module_key": "marketing_automation", "at": old},
                    {"event": "module_details_open", "module_key": "marketing_automation", "at": recent},
                ]
            }
        }
    )
    persist_apps_tools_index_analytics_preferences(tenant, window="24h", compact_mode=False)

    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=10, window=None)

    assert snapshot.window == "24h"
    assert snapshot.total_events == 1
