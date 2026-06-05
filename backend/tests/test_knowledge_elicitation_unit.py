"""Unit tests for OBS2 knowledge elicitation."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.curated_memory_service import CuratedFileKind
from app.application.services.knowledge_elicitation import compose_knowledge_elicitation_snapshot


@pytest.mark.asyncio
async def test_elicitation_detects_gaps() -> None:
    session = AsyncMock()
    bundle: dict[CuratedFileKind, str] = {
        CuratedFileKind.MISSION: "x" * 50,
        CuratedFileKind.IDEAL_STATE: "",
        CuratedFileKind.SOUL: "",
        CuratedFileKind.INSTRUCTIONS: "",
        CuratedFileKind.SKILLS_HIERARCHY: "",
    }
    with (
        patch("app.application.services.knowledge_elicitation.settings") as mock_settings,
        patch(
            "app.application.services.knowledge_elicitation.CuratedMemoryService",
        ) as mock_cls,
    ):
        mock_settings.knowledge_elicitation_enabled = True
        mock_cls.return_value.get_bundle = AsyncMock(return_value=bundle)
        snap = await compose_knowledge_elicitation_snapshot(session, tenant_id=uuid.uuid4())
    assert snap.enabled is True
    assert snap.gap_count >= 1
    assert snap.filled_count >= 1
