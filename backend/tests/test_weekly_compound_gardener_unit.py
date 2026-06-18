"""Unit tests for POS-J1/J2 weekly compound gardener."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.weekly_compound_gardener_service import (
    WeeklyCompoundDraftReviewIn,
    compose_mission_weekly_compound_strip,
    review_weekly_compound_draft,
    run_weekly_compound_gardener_for_tenant,
)
from app.application.services.research_project_service import rank_and_dedupe_research_urls
from app.core.config import settings


@pytest.mark.asyncio
async def test_run_weekly_compound_gardener_creates_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "weekly_compound_gardener_enabled", True)

    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    tenant.id = tenant_id

    reflection = MagicMock()
    reflection.enabled = True
    reflection.message = "2 episodic capture(s) — review patterns in Hive Mind."
    reflection.week_label = "Jun 01 – Jun 07"
    reflection.highlights = []

    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.add = MagicMock()
    session.flush = AsyncMock()

    with patch(
        "app.application.services.weekly_compound_gardener_service.compose_jarvis_weekly_reflection_strip",
        AsyncMock(return_value=reflection),
    ):
        with patch(
            "app.application.services.weekly_compound_gardener_service.compose_knowledge_elicitation_snapshot",
            AsyncMock(
                return_value=MagicMock(
                    prompts=[MagicMock(empty=True, kind="mission", title="Mission", question="What is your mission?")],
                ),
            ),
        ):
            created = await run_weekly_compound_gardener_for_tenant(session, tenant_id=tenant_id)

    assert created == 1
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_compose_mission_weekly_compound_strip_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "weekly_compound_gardener_enabled", False)
    strip = await compose_mission_weekly_compound_strip(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        first_run_complete=True,
    )
    assert strip.enabled is False


def test_rank_and_dedupe_research_urls() -> None:
    urls = [
        "https://example.com/a/",
        "https://www.example.com/a",
        "https://other.com/b",
    ]
    ranked = rank_and_dedupe_research_urls(urls)
    assert len(ranked) == 2
    assert any("other.com" in url for url in ranked)


@pytest.mark.asyncio
async def test_review_weekly_compound_draft_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "weekly_compound_gardener_enabled", True)
    tenant_id = uuid.uuid4()
    draft_id = "draft-abc"
    proposal_id = str(uuid.uuid4())

    tenant = MagicMock()
    tenant.operator_settings = {
        "weekly_compound_gardener": {
            "drafts": [
                {
                    "id": draft_id,
                    "status": "pending",
                    "proposal_id": proposal_id,
                    "created_at": datetime.now(tz=UTC).isoformat(),
                },
            ],
        },
    }

    proposal = MagicMock()
    proposal.tenant_id = tenant_id
    proposal.status = "pending"

    session = AsyncMock()
    session.get = AsyncMock(side_effect=lambda model, pk: tenant if pk == tenant_id else proposal)
    session.flush = AsyncMock()

    result = await review_weekly_compound_draft(
        session,
        tenant_id=tenant_id,
        draft_id=draft_id,
        body=WeeklyCompoundDraftReviewIn(decision="approve"),
    )
    assert result.status == "approved"
    assert proposal.status == "approved"
