"""Unit tests for SB3 capture approve + Obsidian wikilink export."""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.second_brain_capture import (
    SecondBrainCaptureIn,
    approve_capture_note,
    build_capture_markdown,
    build_obsidian_export_markdown,
    list_pending_capture_notes,
    obsidian_safe_filename,
    persist_capture_note,
    resolve_obsidian_wikilink,
)
from app.infrastructure.persistence.models.knowledge import KnowledgeItem


def test_build_obsidian_export_markdown_includes_wikilinks() -> None:
    md = build_capture_markdown(
        idea="Newsletter loop",
        connects_to=["seo-pipeline", "factory-queue"],
        might_use_for="Launch",
        key_tension="Speed vs depth",
    )
    export_md = build_obsidian_export_markdown(
        content_md=md,
        obsidian_filename="newsletter-loop-abc12345",
        connects_to=["seo-pipeline", "factory-queue"],
        wiki_slug_stems={"seo-pipeline", "operator-context"},
    )
    assert "[[seo-pipeline]]" in export_md
    assert "[[factory-queue]]" in export_md
    assert "[[Vault-MOC]]" in export_md


def test_resolve_obsidian_wikilink_matches_wiki_stem() -> None:
    assert resolve_obsidian_wikilink("operator-context", wiki_slug_stems={"operator-context"}) == "operator-context"


@pytest.mark.asyncio
async def test_persist_capture_note_stays_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "second_brain_capture_approve_enabled", True)
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    payload = SecondBrainCaptureIn(
        idea="Test capture pending gate",
        connects_to=["seo-pipeline"],
        might_use_for="Obsidian export",
        key_tension="Approve vs auto",
    )
    out = await persist_capture_note(session, tenant_id=uuid.uuid4(), payload=payload)
    assert out.status == "pending"
    added = session.add.call_args[0][0]
    assert isinstance(added, KnowledgeItem)
    assert added.verified_at is None
    assert "second_brain:pending" in added.topic_tags


@pytest.mark.asyncio
async def test_approve_capture_note_sets_verified_and_wiki_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "wiki_layer_enabled", True)
    monkeypatch.setattr(settings, "second_brain_capture_approve_enabled", True)

    tenant_id = uuid.uuid4()
    capture_id = uuid.uuid4()
    markdown = build_capture_markdown(
        idea="Approved capture note",
        connects_to=["seo-pipeline"],
        might_use_for="Vault export",
        key_tension="Link density",
    )
    row = KnowledgeItem(
        id=capture_id,
        tenant_id=tenant_id,
        source_type="second_brain_capture",
        content_text=markdown,
        confidence_score=0.9,
        topic_tags=["second_brain:capture", "second_brain:pending"],
        decay_factor=1.0,
        scraped_at=datetime.now(tz=UTC),
        verified_at=None,
    )
    session = AsyncMock()
    session.get = AsyncMock(return_value=row)
    session.flush = AsyncMock()

    with patch(
        "app.application.services.wiki_layer_service.WikiLayerService.upsert_custom_page",
        new=AsyncMock(return_value=1),
    ) as upsert:
        result = await approve_capture_note(session, tenant_id=tenant_id, capture_id=capture_id)

    assert result.obsidian_filename.startswith("approved-capture-note-")
    assert result.wiki_slug.startswith("capture-approved-capture-note-")
    assert row.verified_at is not None
    assert "second_brain:approved" in row.topic_tags
    upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_pending_capture_notes_returns_unverified() -> None:
    tenant_id = uuid.uuid4()
    row = KnowledgeItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        source_type="second_brain_capture",
        content_text=build_capture_markdown(
            idea="Pending only",
            connects_to=[],
            might_use_for="",
            key_tension="",
        ),
        confidence_score=0.9,
        topic_tags=["second_brain:pending"],
        decay_factor=1.0,
        scraped_at=datetime.now(tz=UTC),
        verified_at=None,
    )
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[row])))

    pending = await list_pending_capture_notes(session, tenant_id=tenant_id)
    assert len(pending) == 1
    assert pending[0].idea == "Pending only"


@pytest.mark.asyncio
async def test_export_obsidian_includes_approved_capture_file(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.application.services.wiki_layer_service import WikiLayerService
    from app.core.config import settings
    from app.domain.memory.curated import CuratedFileKind

    monkeypatch.setattr(settings, "wiki_layer_enabled", True)

    tenant_id = uuid.uuid4()
    capture_id = uuid.uuid4()
    markdown = build_capture_markdown(
        idea="Export me",
        connects_to=["Brain-Pack"],
        might_use_for="Obsidian",
        key_tension="Manual vs auto",
    )
    capture = KnowledgeItem(
        id=capture_id,
        tenant_id=tenant_id,
        source_type="second_brain_capture",
        content_text=markdown,
        confidence_score=0.9,
        topic_tags=["second_brain:approved"],
        decay_factor=1.0,
        scraped_at=datetime.now(tz=UTC),
        verified_at=datetime.now(tz=UTC),
    )
    expected_name = obsidian_safe_filename(idea="Export me", capture_id=capture_id)

    db = AsyncMock()
    svc = WikiLayerService(db=db)

    curated_bundle = {
        CuratedFileKind.MISSION: "Mission",
        CuratedFileKind.IDEAL_STATE: "",
        CuratedFileKind.SOUL: "",
        CuratedFileKind.SKILLS_HIERARCHY: "",
        CuratedFileKind.INSTRUCTIONS: "# Instructions",
    }

    with (
        patch(
            "app.application.services.wiki_layer_service.CuratedMemoryService.get_bundle",
            new=AsyncMock(return_value=curated_bundle),
        ),
        patch(
            "app.application.services.wiki_layer_service.CuratedMemoryService.render_brain_pack_export",
            return_value="# Brain Pack",
        ),
        patch.object(svc, "list_wiki_pages", new=AsyncMock(return_value=[])),
        patch.object(svc, "_fetch_approved_capture_knowledge", new=AsyncMock(return_value=[capture])),
    ):
        payload = await svc.export_obsidian_vault(tenant_id)

    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        names = zf.namelist()
        assert f"captures/{expected_name}.md" in names
        capture_body = zf.read(f"captures/{expected_name}.md").decode()
        assert "[[Brain-Pack]]" in capture_body
        moc = zf.read("Vault-MOC.md").decode()
        assert f"[[{expected_name}]]" in moc
