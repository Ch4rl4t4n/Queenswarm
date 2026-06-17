"""Unit tests for MEM5 client/project memory tags + recall filter."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from datetime import UTC, datetime

import pytest

from app.application.services.cited_recall_service import CitedRecallSourceOut, derive_cited_recall
from app.application.services.memory_project_tags_service import (
    ActiveRecallFilterPatch,
    MemoryProjectTagUpsertIn,
    compose_memory_project_tags_snapshot,
    parse_memory_project_tag_ids_from_topic_tags,
    resolve_recall_filter_tag_ids,
    set_active_recall_filter,
    source_matches_memory_project_filter,
    topic_tag_for_memory_project,
    upsert_memory_project_tag,
)
from app.infrastructure.persistence.models.knowledge import KnowledgeItem


def test_topic_tag_roundtrip() -> None:
    token = topic_tag_for_memory_project("acme-corp")
    assert token == "mem5:acme-corp"
    assert parse_memory_project_tag_ids_from_topic_tags([token, "social-intel"]) == ["acme-corp"]


def test_source_matches_filter_rls() -> None:
    assert source_matches_memory_project_filter(source_tag_ids=[], filter_tag_ids=[]) is True
    assert source_matches_memory_project_filter(source_tag_ids=[], filter_tag_ids=["acme"]) is False
    assert source_matches_memory_project_filter(source_tag_ids=["acme"], filter_tag_ids=["acme"]) is True
    assert source_matches_memory_project_filter(source_tag_ids=["other"], filter_tag_ids=["acme"]) is False


def test_upsert_and_active_filter_on_tenant() -> None:
    tenant = MagicMock()
    tenant.id = uuid.uuid4()
    tenant.operator_settings = {}
    row = upsert_memory_project_tag(
        tenant,
        MemoryProjectTagUpsertIn(id="acme", label="Acme Corp", kind="client"),
    )
    assert row.id == "acme"
    active = set_active_recall_filter(tenant, ActiveRecallFilterPatch(tag_ids=["acme"]))
    assert active == ["acme"]
    resolved = resolve_recall_filter_tag_ids(tenant, requested_tag_ids=None)
    assert resolved == ["acme"]


def test_derive_cited_recall_applies_mem5_slice() -> None:
    hive = [
        CitedRecallSourceOut(
            source_id="hive:del-1",
            source_type="hive_mind",
            label="HiveMind · acme brief",
            snippet="Acme launch checklist.",
            similarity=0.88,
            href="/knowledge?tab=outputs",
        ),
        CitedRecallSourceOut(
            source_id="hive:del-2",
            source_type="hive_mind",
            label="HiveMind · other client",
            snippet="Other client notes.",
            similarity=0.85,
            href="/knowledge?tab=outputs",
        ),
    ]
    tag_map = {
        "hive:del-1": ["acme"],
        "hive:del-2": ["other"],
    }
    out = derive_cited_recall(
        query="acme launch",
        curated_hits=[],
        hive_hits=hive,
        session_hits=[],
        vault_hits=[],
        filter_tag_ids=["acme"],
        filter_labels=["Acme Corp"],
        source_tag_ids_by_id=tag_map,
    )
    assert out.filter_active is True
    assert len(out.citations) == 1
    assert out.citations[0].source_id == "hive:del-1"
    assert "MEM5 slice active" in out.operator_hint


@pytest.mark.asyncio
async def test_compose_snapshot_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "memory_project_tags_enabled", False)
    session = AsyncMock()
    tenant = MagicMock(operator_settings={})
    snapshot = await compose_memory_project_tags_snapshot(
        session,
        tenant_id=uuid.uuid4(),
        tenant=tenant,
    )
    assert snapshot.enabled is False


@pytest.mark.asyncio
async def test_compose_snapshot_counts_knowledge_tags() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock(
        operator_settings={
            "memory_project_tags": {
                "tags": [
                    {
                        "id": "acme",
                        "label": "Acme",
                        "kind": "client",
                        "created_at": "2026-06-05T00:00:00+00:00",
                    },
                ],
                "active_filter_tag_ids": [],
            },
        },
    )
    row = KnowledgeItem(
        tenant_id=tenant_id,
        source_type="note",
        content_text="Acme project notes",
        topic_tags=["mem5:acme"],
        scraped_at=datetime.now(tz=UTC),
    )
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))
    snapshot = await compose_memory_project_tags_snapshot(session, tenant_id=tenant_id, tenant=tenant)
    assert snapshot.enabled is True
    assert snapshot.tags[0].knowledge_count == 1
