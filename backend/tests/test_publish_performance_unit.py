"""Publish Performance Loop — aggregation and insights."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.publish_performance import build_publish_performance_snapshot


def test_build_publish_performance_snapshot_empty() -> None:
    snap = build_publish_performance_snapshot(None, window_days=30)
    assert snap.enabled is True
    assert snap.totals.get("events", 0) == 0
    assert snap.live_posts == 0


def test_build_publish_performance_snapshot_counts_simulate() -> None:
    from types import SimpleNamespace

    tenant = SimpleNamespace(
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "at": datetime.now(tz=UTC).isoformat(),
                        "event_type": "publish_social_simulate",
                        "message": "Simulated instagram post",
                        "payload": {"channel": "instagram", "ok": True},
                    },
                    {
                        "at": datetime.now(tz=UTC).isoformat(),
                        "event_type": "publish_queue_approved",
                        "message": "Approved pack",
                        "payload": {"channel": "instagram"},
                    },
                ],
            },
        },
    )
    snap = build_publish_performance_snapshot(tenant, window_days=30)
    assert snap.totals["social_simulate"] == 1
    assert snap.totals["queue_approved"] == 1
    assert snap.simulate_success_rate_pct == 100.0
    assert len(snap.by_channel) == 1
    assert snap.by_channel[0].channel == "instagram"


def test_build_publish_performance_insight_ready_for_live() -> None:
    from types import SimpleNamespace

    rows = [
        {
            "at": datetime.now(tz=UTC).isoformat(),
            "event_type": "publish_social_simulate",
            "message": f"Sim {i}",
            "payload": {"channel": "instagram", "ok": True},
        }
        for i in range(3)
    ]
    tenant = SimpleNamespace(
        operator_settings={
            "execution_studio": {
                "recent_activity": rows,
            },
        },
    )
    snap = build_publish_performance_snapshot(tenant, window_days=30)
    ids = [i.id for i in snap.insights]
    assert "ready_for_live" in ids
