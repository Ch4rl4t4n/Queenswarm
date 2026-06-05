"""Unit tests for CBO dispatch bridge (BA6)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.business_operator_dispatch import (
    BusinessOperatorDispatchIn,
    dispatch_business_operator_action,
    resolve_dispatch_template,
)


def test_resolve_dispatch_template_mission_triage_uses_flush() -> None:
    template = resolve_dispatch_template(
        action_id="mission_triage",
        lane="mission",
        title="Review triage",
        detail="2 waiting",
    )
    assert template.mode == "triage_flush"


def test_resolve_dispatch_template_factory_lane_supervisor() -> None:
    template = resolve_dispatch_template(
        action_id="gumroad_first_upload",
        lane="revenue",
        title="Factory queue",
        detail="Audit exports",
    )
    assert template.mode == "supervisor_session"
    assert "skill-authoring-template" in template.skills


def test_resolve_dispatch_template_marketing_uses_kanban() -> None:
    template = resolve_dispatch_template(
        action_id="daily_marketing",
        lane="marketing",
        title="Post draft",
        detail="LinkedIn",
    )
    assert template.mode == "mission_kanban"


@pytest.mark.asyncio
async def test_dispatch_supervisor_session_when_ops_lane() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    body = BusinessOperatorDispatchIn(
        action_id="open_agents",
        lane="ops",
        title="Start session",
        detail="No blockers",
    )
    sup = MagicMock()
    sup.id = uuid.uuid4()

    with (
        patch("app.application.services.business_operator_dispatch.settings") as mock_settings,
        patch(
            "app.application.services.business_operator_dispatch.create_supervisor_session",
            new_callable=AsyncMock,
            return_value=sup,
        ) as mock_create,
    ):
        mock_settings.operator_control_plane_enabled = True
        mock_settings.supervisor_dynamic_subagents_enabled = True
        mock_settings.supervisor_durable_mode_enabled = False
        mock_settings.supervisor_default_runtime_mode = "inprocess"

        result = await dispatch_business_operator_action(
            session,
            tenant_id=tenant_id,
            created_by_subject="admin@queenswarm.love",
            body=body,
        )

    assert result.kind == "supervisor_session"
    assert result.supervisor_session_id == sup.id
    mock_create.assert_awaited_once()
    call_kwargs = mock_create.await_args.kwargs
    assert call_kwargs["tenant_id"] == tenant_id
    assert len(call_kwargs["roles"]) <= 3


@pytest.mark.asyncio
async def test_dispatch_disabled_when_control_plane_off() -> None:
    with patch("app.application.services.business_operator_dispatch.settings") as mock_settings:
        mock_settings.operator_control_plane_enabled = False
        with pytest.raises(ValueError, match="disabled"):
            await dispatch_business_operator_action(
                AsyncMock(),
                tenant_id=uuid.uuid4(),
                created_by_subject="x",
                body=BusinessOperatorDispatchIn(
                    action_id="open_agents",
                    lane="ops",
                    title="x",
                ),
            )
