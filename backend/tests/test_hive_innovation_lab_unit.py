"""Unit tests for Hive Innovation Lab."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.hive_innovation_lab import (
    InnovationBrainstormRequest,
    _infer_feature_modules,
    brainstorm_innovation_proposal,
    implement_innovation_proposal,
    review_innovation_proposal,
)


def test_infer_feature_modules_hotline() -> None:
    mods = _infer_feature_modules("Add bee hotline to cockpit telegram")
    assert "bee_hotline" in mods
    assert "zero_ui_mode" in mods


@pytest.mark.asyncio
async def test_brainstorm_creates_proposal() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    with patch("app.application.services.hive_innovation_lab.settings") as mock_settings:
        mock_settings.hive_innovation_lab_enabled = True
        out = await brainstorm_innovation_proposal(
            session,
            tenant_id=uuid.uuid4(),
            body=InnovationBrainstormRequest(
                prompt="Add Hive Oracle warnings to cockpit with trust autopilot",
                category="feature",
            ),
        )
    assert out.title.startswith("Innovation:")
    assert "hive_oracle" in out.feature_modules
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_innovation_lab_e2e_when_approved_then_queues_maintainer() -> None:
    """research-to-pr-proposal flow: brainstorm → approve → implement handoff."""

    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    proposal_row = MagicMock()
    proposal_row.id = uuid.uuid4()
    proposal_row.tenant_id = tenant_id
    proposal_row.proposal_type = "hive_innovation_lab"
    proposal_row.title = "Innovation: test"
    proposal_row.description = "desc"
    proposal_row.status = "pending"
    proposal_row.risk_level = "medium"
    proposal_row.impact_score = 0.72
    proposal_row.proposal_payload = {
        "source_prompt": "Add GA4 connector preset",
        "feature_modules": ["hive_innovation_lab"],
        "implementation_plan_md": "# plan\n" + ("Safe implementation steps with tests. " * 5),
        "suggested_paths": ["backend/app/infrastructure/connectors/phase3/catalog.py"],
        "trust_lane": "simulate",
    }
    proposal_row.supervisor_session_id = None
    proposal_row.sub_agent_session_id = None
    proposal_row.created_at = None
    proposal_row.implemented_at = None

    approved_row = MagicMock()
    approved_row.id = proposal_row.id
    approved_row.tenant_id = tenant_id
    approved_row.proposal_type = "hive_innovation_lab"
    approved_row.title = proposal_row.title
    approved_row.description = proposal_row.description
    approved_row.status = "approved"
    approved_row.risk_level = "medium"
    approved_row.impact_score = 0.72
    approved_row.proposal_payload = dict(proposal_row.proposal_payload)
    approved_row.supervisor_session_id = None
    approved_row.sub_agent_session_id = None
    approved_row.created_at = None
    approved_row.implemented_at = None

    codebase_row = MagicMock()
    codebase_row.id = uuid.uuid4()

    tenant = MagicMock()
    tenant.id = tenant_id

    async def _scalar(_query: object) -> MagicMock | None:
        return approved_row

    session.scalar = AsyncMock(side_effect=_scalar)

    with (
        patch("app.application.services.hive_innovation_lab.settings") as mock_settings,
        patch(
            "app.application.services.hive_innovation_lab.brainstorm_innovation_proposal",
            new_callable=AsyncMock,
        ) as mock_brainstorm,
        patch(
            "app.application.services.hive_innovation_lab.review_agent_suggestion",
            new_callable=AsyncMock,
        ) as mock_review,
        patch(
            "app.application.services.hive_innovation_lab.assess_innovation_viability",
            new_callable=AsyncMock,
        ) as mock_viability,
        patch(
            "app.application.services.execution_studio_handoff.create_codebase_execution_proposal",
            new_callable=AsyncMock,
            return_value=codebase_row,
        ),
        patch(
            "app.application.services.execution_studio_handoff.trigger_maintainer_with_proposal_goal",
            new_callable=AsyncMock,
            return_value={"ok": True, "goal_id": "goal_test"},
        ),
    ):
        mock_settings.hive_innovation_lab_enabled = True
        mock_settings.queen_maintainer_enabled = True
        mock_brainstorm.return_value = MagicMock(id=str(proposal_row.id), status="pending")
        mock_review.return_value = approved_row
        mock_viability.return_value = MagicMock(ok=True, model_dump=lambda mode="json": {"ok": True})

        reviewed = await review_innovation_proposal(
            session,
            tenant_id=tenant_id,
            proposal_id=proposal_row.id,
            decision="approved",
            reviewer_subject="operator@test",
        )
        assert reviewed.status == "approved"

        result = await implement_innovation_proposal(
            session,
            tenant=tenant,
            proposal_id=proposal_row.id,
            reviewer_subject="operator@test",
        )
        assert result["ok"] is True
        assert result["codebase_proposal_id"] == str(codebase_row.id)
