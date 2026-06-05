"""Second Brain Pack wizard unit tests."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.second_brain_wizard import compose_second_brain_wizard
from app.domain.memory.curated import CuratedFileKind


@pytest.mark.asyncio
async def test_compose_second_brain_wizard_progress(monkeypatch) -> None:
    tenant_id = uuid.uuid4()

    class FakeSvc:
        async def get_bundle(self, _tenant_id: uuid.UUID) -> dict[CuratedFileKind, str]:
            return {
                CuratedFileKind.SOUL: "identity",
                CuratedFileKind.MISSION: "goals",
                CuratedFileKind.INSTRUCTIONS: "prefs",
                CuratedFileKind.SKILLS_HIERARCHY: "",
                CuratedFileKind.IDEAL_STATE: "",
            }

    monkeypatch.setattr(
        "app.application.services.second_brain_wizard.CuratedMemoryService",
        lambda db: FakeSvc(),
    )
    monkeypatch.setattr(
        "app.application.services.second_brain_wizard.get_solo_trio_status",
        AsyncMock(
            return_value={
                "lanes_bound": 1,
                "lanes": [{"last_run_at": None, "last_session_id": None}],
            },
        ),
    )

    obsidian = SimpleNamespace(is_active=False)

    async def fake_fetch(_session, *, slug: str):
        del slug
        return obsidian

    monkeypatch.setattr(
        "app.application.services.second_brain_wizard.DynamicConnectorService",
        lambda: SimpleNamespace(fetch_by_slug=fake_fetch),
    )
    monkeypatch.setattr("app.application.services.second_brain_wizard.settings.solo_mode_enabled", True)

    out = await compose_second_brain_wizard(AsyncMock(), tenant_id=tenant_id)
    assert out.enabled is True
    assert out.brain_pack_filled >= 3
    assert out.steps[0].done is True
    assert out.progress_pct >= 33
