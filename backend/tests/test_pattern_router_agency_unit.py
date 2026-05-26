"""Pattern router LLM wiring + media agency snapshot tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.media_agency_in_a_box import compose_media_agency_snapshot
from app.application.services.supervisor.pattern_router import PATTERN_RAG, PatternSelection, select_patterns_for_task
from app.application.services.supervisor.session_service import create_supervisor_session
from app.application.services.supervisor.shared_context import SharedContextService


@pytest.mark.asyncio
async def test_create_supervisor_session_applies_llm_pattern_refine(monkeypatch: pytest.MonkeyPatch) -> None:
    """When LLM router flag is on, session stores refined pattern stack."""

    class _FakeDb:
        def add(self, _row: object) -> None:
            return None

        async def flush(self) -> None:
            return None

        async def get(self, _model: object, _id: object) -> None:
            return None

    async def _append_event(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    async def _run_sub(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    heuristic = select_patterns_for_task(goal="Research competitor landing pages", roles=["researcher"])
    refined = PatternSelection(
        primary=[*heuristic.primary, PATTERN_RAG] if PATTERN_RAG not in heuristic.primary else list(heuristic.primary),
        secondary=list(heuristic.secondary),
        forced_reflection=heuristic.forced_reflection,
        resource_aware=heuristic.resource_aware,
        rationale=[*heuristic.rationale, "llm refine: needs retrieval"],
        router_version="heuristic-v1+llm-v1",
    )

    monkeypatch.setattr("app.application.services.supervisor.session_service.append_event", _append_event)
    monkeypatch.setattr("app.application.services.supervisor.session_service.run_sub_agent_inprocess", _run_sub)
    monkeypatch.setattr("app.application.services.supervisor.session_service.settings.supervisor_skills_enabled", False)
    monkeypatch.setattr("app.application.services.supervisor.session_service.settings.supervisor_pattern_router_enabled", True)
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.settings.supervisor_pattern_router_llm_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.supervisor.session_service.refine_pattern_selection_with_llm",
        AsyncMock(return_value=refined),
    )

    session_row = await create_supervisor_session(
        _FakeDb(),
        goal="Research competitor landing pages",
        created_by_subject="tester",
        runtime_mode="inprocess",
        roles=["researcher"],
        shared_context=SharedContextService(),
    )

    patterns = dict(session_row.context_summary or {}).get("agentic_patterns") or {}
    assert patterns.get("router_version") == "heuristic-v1+llm-v1"
    assert PATTERN_RAG in list(patterns.get("primary") or [])


@pytest.mark.asyncio
async def test_compose_media_agency_snapshot_enabled() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(
        operator_settings={
            "white_label": {"brand_name": "Agency Co", "hide_platform_branding": True},
        },
    )

    with (
        patch("app.application.services.media_agency_in_a_box.settings") as mock_settings,
        patch(
            "app.application.services.media_agency_in_a_box.compose_publish_onboarding_snapshot",
            new_callable=AsyncMock,
        ) as onboard_mock,
        patch(
            "app.application.services.media_agency_in_a_box.build_publish_performance_snapshot",
        ) as perf_mock,
    ):
        mock_settings.media_agency_in_a_box_enabled = True
        from datetime import UTC, datetime

        from app.application.services.publish_operator_onboarding import PublishOnboardingSnapshotOut

        onboard_mock.return_value = PublishOnboardingSnapshotOut(
            generated_at=datetime.now(tz=UTC),
            progress_pct=60,
        )
        perf_mock.return_value = SimpleNamespace(
            live_posts=1,
            totals={"social_simulate": 2},
            by_channel=[],
        )

        snap = await compose_media_agency_snapshot(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            tenant=tenant,
        )

    assert snap.enabled is True
    assert snap.brand_name == "Agency Co"
    assert snap.white_label_ready is True
    assert len(snap.client_lanes) == 3
