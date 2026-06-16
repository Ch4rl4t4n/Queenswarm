"""Unit tests for Track M LOC13 analytics local sovereign integration."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.analytics_local_inference_service import (
    append_local_inference_goal_note,
    build_analytics_session_local_context,
    resolve_analytics_local_inference,
)


@pytest.mark.asyncio
async def test_resolve_analytics_local_inference_inactive_cloud_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_local_sovereign_prefer_enabled", True)
    monkeypatch.setattr(config.settings, "local_llm_enabled", True)
    monkeypatch.setattr(config.settings, "llm_airgap", False)
    with patch(
        "app.application.services.analytics_local_inference_service.load_routing_config",
        new=AsyncMock(return_value={"routing_mode": "quality"}),
    ):
        local = await resolve_analytics_local_inference(AsyncMock(), tenant_id=uuid.uuid4())
    assert local.active is False
    assert local.routing_mode == "quality"


@pytest.mark.asyncio
async def test_resolve_analytics_local_inference_active_sovereign_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_local_sovereign_prefer_enabled", True)
    monkeypatch.setattr(config.settings, "local_llm_enabled", True)
    monkeypatch.setattr(config.settings, "llm_airgap", False)
    monkeypatch.setattr(config.settings, "ollama_default_model", "ollama/qwen2.5:7b")
    with patch(
        "app.application.services.analytics_local_inference_service.load_routing_config",
        new=AsyncMock(return_value={"routing_mode": "local_sovereign"}),
    ):
        local = await resolve_analytics_local_inference(AsyncMock(), tenant_id=uuid.uuid4())
    assert local.active is True
    assert local.local_model_slug == "ollama/qwen2.5:7b"
    assert "Local sovereign" in local.operator_hint


@pytest.mark.asyncio
async def test_resolve_analytics_local_inference_airgap_forces_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_local_sovereign_prefer_enabled", True)
    monkeypatch.setattr(config.settings, "local_llm_enabled", True)
    monkeypatch.setattr(config.settings, "llm_airgap", True)
    local = await resolve_analytics_local_inference(AsyncMock(), tenant_id=None)
    assert local.active is True
    assert local.airgap is True


def test_build_analytics_session_local_context_when_active() -> None:
    from app.application.services.analytics_local_inference_service import AnalyticsLocalInferenceOut

    ctx = build_analytics_session_local_context(
        AnalyticsLocalInferenceOut(active=True, local_model_slug="ollama/qwen2.5:7b"),
    )
    assert ctx["analytics_local_sovereign"] is True
    assert ctx["analytics_prefer_local_model"] == "ollama/qwen2.5:7b"


def test_append_local_inference_goal_note() -> None:
    from app.application.services.analytics_local_inference_service import AnalyticsLocalInferenceOut

    goal = append_local_inference_goal_note(
        goal="Base analytics goal.",
        local=AnalyticsLocalInferenceOut(active=True, local_model_slug="ollama/qwen2.5:7b"),
    )
    assert "LOCAL INFERENCE" in goal
    assert "ollama/qwen2.5:7b" in goal


@pytest.mark.asyncio
async def test_compose_analytics_workspace_snapshot_includes_local_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.analytics_workspace_service import compose_analytics_workspace_snapshot
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_workspace_enabled", True)
    monkeypatch.setattr(config.settings, "analytics_connector_profile_enabled", False)
    with (
        patch(
            "app.application.services.virtual_company_swarm_builder.list_built_wizard_templates",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.application.services.analytics_local_inference_service.load_routing_config",
            new=AsyncMock(return_value={"routing_mode": "local_sovereign"}),
        ),
    ):
        snap = await compose_analytics_workspace_snapshot(AsyncMock(), tenant_id=uuid.uuid4())
    assert snap.local_sovereign_active is True
    assert snap.local_model_slug is not None


@pytest.mark.asyncio
async def test_submit_wizard_seeds_local_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.application.services.analytics_business_question_wizard_service import (
        BusinessQuestionSubmitIn,
        submit_business_question_wizard,
    )
    from app.core import config

    monkeypatch.setattr(config.settings, "analytics_question_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", False)
    monkeypatch.setattr(config.settings, "analytics_local_sovereign_prefer_enabled", True)
    monkeypatch.setattr(config.settings, "local_llm_enabled", True)
    monkeypatch.setattr(config.settings, "llm_airgap", True)

    task_id = uuid.uuid4()
    deliverable_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fake_snap = SimpleNamespace(id=task_id, title="Brief")
    fake_deliverable = SimpleNamespace(id=deliverable_id)
    fake_sup = SimpleNamespace(id=session_id)

    mock_create = AsyncMock(return_value=fake_sup)
    from app.application.services.analytics_local_inference_service import AnalyticsLocalInferenceOut

    with (
        patch(
            "app.application.services.analytics_business_question_wizard_service.create_mission_triage_task",
            new=AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.analytics_business_question_wizard_service.OutputEngine.create_final_deliverable",
            new=AsyncMock(return_value=fake_deliverable),
        ),
        patch(
            "app.application.services.analytics_business_question_wizard_service.create_supervisor_session",
            new=mock_create,
        ),
        patch(
            "app.application.services.analytics_local_inference_service.resolve_analytics_local_inference",
            new=AsyncMock(
                return_value=AnalyticsLocalInferenceOut(
                    active=True,
                    local_model_slug="ollama/qwen2.5:7b",
                    airgap=True,
                ),
            ),
        ),
    ):
        await submit_business_question_wizard(
            AsyncMock(),
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="test",
            body=BusinessQuestionSubmitIn(
                business_question="Why did weekly active users drop 12% in May?",
                date_range_preset="last_30d",
                sources=["ga4"],
                dispatch_session=True,
            ),
        )
    seed = mock_create.await_args.kwargs["context_seed"]
    assert seed.get("analytics_local_sovereign") is True
