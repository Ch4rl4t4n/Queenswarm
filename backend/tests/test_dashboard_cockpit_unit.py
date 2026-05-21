"""Tests for aggregated dashboard cockpit bundle."""

from __future__ import annotations

from app.application.services.dashboard_cockpit import CockpitSystemLite, DashboardCockpitPayload


def test_dashboard_cockpit_payload_accepts_nested_summary() -> None:
    payload = DashboardCockpitPayload(
        generated_at="2026-05-21T12:00:00+00:00",
        revision=1_746_000_000,
        agents=[],
        recent_tasks=[],
        summary={
            "generated_at": "2026-05-21T12:00:00+00:00",
            "agents": {"total": 0, "by_status": {}, "by_hive_tier": {}},
            "tasks": {"pending": 0},
        },
        system_status=CockpitSystemLite(
            agents_total=0,
            agents_running=0,
            tasks_running=0,
            tasks_pending=0,
            llm_grok=False,
            llm_anthropic=False,
        ),
    )
    dumped = payload.model_dump(mode="json")
    assert dumped["summary"]["agents"]["total"] == 0
    assert dumped["revision"] == 1_746_000_000
    assert dumped["system_status"]["tasks_pending"] == 0


def test_cockpit_system_lite_defaults_llm_flags_false() -> None:
    lite = CockpitSystemLite(
        agents_total=3,
        agents_running=1,
        tasks_running=2,
        tasks_pending=4,
    )
    assert lite.llm_grok is False
    assert lite.llm_anthropic is False
