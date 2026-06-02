"""Unit tests for solo operator first-run wizard."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from datetime import UTC, datetime

import pytest

from app.application.services.solo_operator_first_run import (
    STARTER_PROJECT_BRIEF,
    _brief_is_ready,
    apply_starter_project_brief,
    compose_solo_first_run,
)
from app.domain.memory.curated import CuratedFileKind, CuratedMemoryFile


def test_brief_is_ready_when_project_marker_present() -> None:
    long_brief = f"PROJECT: Test\nGoal: x\n{'detail line ' * 20}"
    assert _brief_is_ready(long_brief) is True
    assert _brief_is_ready("short") is False


@pytest.mark.asyncio
async def test_compose_solo_first_run_all_pending() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    instructions = CuratedMemoryFile(
        tenant_id=tenant_id,
        kind=CuratedFileKind.INSTRUCTIONS,
        content_md="",
        version=1,
        char_count=0,
        updated_at=datetime.now(tz=UTC),
        updated_by_user_id=None,
    )

    with (
        patch("app.application.services.solo_operator_first_run.settings") as mock_settings,
        patch(
            "app.application.services.solo_operator_first_run.provider_effective_grok",
            return_value="",
        ),
        patch(
            "app.application.services.solo_operator_first_run.provider_effective_anthropic",
            return_value="",
        ),
        patch(
            "app.application.services.solo_operator_first_run.provider_effective_openai",
            return_value="",
        ),
        patch(
            "app.application.services.solo_operator_first_run.CuratedMemoryService",
        ) as svc_cls,
    ):
        mock_settings.solo_mode_enabled = True
        mock_settings.operator_loop_enabled = False
        svc = svc_cls.return_value
        svc.get = AsyncMock(return_value=instructions)

        snapshot = await compose_solo_first_run(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
        )

    assert snapshot.enabled is True
    assert snapshot.complete is False
    assert snapshot.progress_pct == 0
    assert len(snapshot.steps) == 3
    assert snapshot.steps[0].id == "llm_keys"
    assert snapshot.steps[0].done is False


@pytest.mark.asyncio
async def test_apply_starter_project_brief_when_empty() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with patch(
        "app.application.services.solo_operator_first_run.CuratedMemoryService",
    ) as svc_cls:
        svc = svc_cls.return_value
        svc.get = AsyncMock(return_value=None)
        svc.upsert = AsyncMock(return_value=MagicMock())

        result = await apply_starter_project_brief(
            session,
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
        )

    assert result["ok"] is True
    assert result["applied"] is True
    svc.upsert.assert_awaited_once()
    args = svc.upsert.await_args.args
    assert args[1] == CuratedFileKind.INSTRUCTIONS
    assert STARTER_PROJECT_BRIEF.strip() in args[2]
