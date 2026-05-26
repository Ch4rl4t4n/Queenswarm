"""Phase 4 — Execution Studio supervisor context + activity feed."""

from __future__ import annotations

import uuid

import pytest

from app.application.services.execution_studio_activity import (
    append_execution_activity,
    list_execution_activity,
)
from app.application.services.execution_studio_context import (
    augment_skill_slugs_for_execution,
    detect_execution_domain,
    enrich_supervisor_session_summary,
    execution_prompt_from_summary,
)
from app.infrastructure.persistence.models.tenant import Tenant


def test_detect_execution_domain_hybrid() -> None:
    """Goals mentioning both connectors and codebase classify as hybrid."""

    assert detect_execution_domain("Connect Notion and refactor backend pytest suite") == "hybrid"


def test_detect_execution_domain_internal() -> None:
    """Maintainer-style goals classify as internal."""

    assert detect_execution_domain("Run Queen Maintainer on tech debt") == "internal"


def test_augment_skill_slugs_adds_execution_studio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Execution goals auto-attach execution-studio skill."""

    class _Settings:
        execution_studio_enabled = True

    monkeypatch.setattr(
        "app.application.services.execution_studio_context.get_settings",
        lambda: _Settings(),
    )

    merged = augment_skill_slugs_for_execution("fix bug in github repo", skill_slugs=["research"])
    assert merged is not None
    assert "execution-studio" in merged
    assert "research" in merged


def test_enrich_supervisor_session_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Context summary receives execution_studio block when enabled."""

    class _Settings:
        execution_studio_enabled = True

    monkeypatch.setattr(
        "app.application.services.execution_studio_context.get_settings",
        lambda: _Settings(),
    )

    tenant = Tenant(id=uuid.uuid4(), name="demo", operator_settings={})
    summary = enrich_supervisor_session_summary(
        {"raw_goal": "post to slack"},
        tenant=tenant,
        goal="post to slack channel",
        roles=["researcher", "coder"],
    )
    block = summary.get("execution_studio")
    assert isinstance(block, dict)
    assert block.get("execution_domain") == "external"
    assert "prompt_block" in block


def test_execution_prompt_from_summary() -> None:
    """Prompt block extracts from nested context."""

    text = execution_prompt_from_summary(
        {"execution_studio": {"prompt_block": "## Execution Studio\nhello"}},
    )
    assert "Execution Studio" in text


def test_activity_ring_buffer() -> None:
    """Activity events cap at MAX and return newest first."""

    tenant = Tenant(id=uuid.uuid4(), name="demo", operator_settings={})
    for idx in range(3):
        append_execution_activity(
            tenant,
            event_type="tool_execute",
            message=f"event-{idx}",
            payload={"idx": idx},
        )
    rows = list_execution_activity(tenant, limit=2)
    assert len(rows) == 2
    assert rows[0]["message"] == "event-2"
