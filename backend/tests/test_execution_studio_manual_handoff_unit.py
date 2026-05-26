"""Tests for Execution Studio manual and codebase handoff."""

from __future__ import annotations

import uuid

import pytest

from app.application.services.execution_studio_manual import build_execution_studio_manual


def test_manual_full_has_sections() -> None:
    """Full manual returns ordered sections for UI and agents."""

    manual = build_execution_studio_manual()
    assert manual["title"]
    sections = manual.get("sections")
    assert isinstance(sections, list)
    assert len(sections) >= 5
    ids = {str(sec.get("id")) for sec in sections}
    assert "research_to_execution" in ids
    assert "agent_reference" in ids


def test_manual_section_lookup() -> None:
    """Section slug returns single section envelope."""

    out = build_execution_studio_manual(section_id="internal_codebase")
    assert out.get("found") is True
    assert out.get("section", {}).get("id") == "internal_codebase"


def test_manual_unknown_section() -> None:
    """Unknown section id returns found=false."""

    out = build_execution_studio_manual(section_id="does-not-exist")
    assert out.get("found") is False


@pytest.mark.asyncio
async def test_create_codebase_proposal_pending() -> None:
    """Codebase proposals always start pending with manual ref."""

    from app.application.services.execution_studio_handoff import (
        CODEBASE_PROPOSAL_TYPE,
        create_codebase_execution_proposal,
    )

    class _Session:
        def add(self, _row: object) -> None:
            return None

        async def flush(self) -> None:
            return None

    row = await create_codebase_execution_proposal(
        _Session(),  # type: ignore[arg-type]
        tenant_id=uuid.uuid4(),
        supervisor_session_id=None,
        sub_agent_session_id=None,
        proposed_by_role="researcher",
        title="Optimize connector refresh",
        description="Sync OAuth refresh tokens to hub before invoke.",
        goal_excerpt="Implement dual-write on token refresh in dynamic hub.",
    )
    assert row.proposal_type == CODEBASE_PROPOSAL_TYPE
    assert row.status == "pending"
    assert row.proposal_payload.get("manual_ref")
